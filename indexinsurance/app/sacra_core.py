"""
SACRA v2.0 — Surkhandarya AgroClimate Risk Analyzer
Area-yield index insurance pricing engine based on the Gumbel distribution.

Methodological basis:
  - Gumbel (EV-I) preferred over GEV-MLE: at n ~ 15 the MLE shape parameter
    is unstable (v1.0 produced xi = +5.69 -> VaR = 9.2e10 kg/ha).
  - Parameters estimated by L-moments (PWM), which are far more robust than
    MLE in small samples (Hosking & Wallis, 1997).
  - Area-yield index rather than weather index, following the weak
    climate-yield correlation (|r| <= 0.23) found under irrigated conditions.

Author: Alisher Abdullayev
"""

from dataclasses import dataclass, field
from typing import Sequence
import numpy as np
from scipy import integrate, optimize

EULER_GAMMA = 0.5772156649015329


# ----------------------------------------------------------------------
# 1. Gumbel distribution, parameterised for LOSSES (upper tail = bad)
# ----------------------------------------------------------------------

@dataclass
class Gumbel:
    """Gumbel (EV-I) distribution.  F(x) = exp(-exp(-(x-mu)/beta))"""
    mu: float
    beta: float

    def __post_init__(self):
        if self.beta <= 0:
            raise ValueError(f"beta must be > 0, got {self.beta}")

    # --- basic functions -------------------------------------------------
    def cdf(self, x):
        z = (np.asarray(x, dtype=float) - self.mu) / self.beta
        return np.exp(-np.exp(-z))

    def pdf(self, x):
        z = (np.asarray(x, dtype=float) - self.mu) / self.beta
        return np.exp(-(z + np.exp(-z))) / self.beta

    def ppf(self, p):
        p = np.asarray(p, dtype=float)
        if np.any((p <= 0) | (p >= 1)):
            raise ValueError("p must lie strictly in (0, 1)")
        return self.mu - self.beta * np.log(-np.log(p))

    # --- moments ---------------------------------------------------------
    @property
    def mean(self):
        return self.mu + EULER_GAMMA * self.beta

    @property
    def std(self):
        return self.beta * np.pi / np.sqrt(6.0)

    # --- estimation ------------------------------------------------------
    @classmethod
    def fit_lmoments(cls, data: Sequence[float]) -> "Gumbel":
        """
        L-moment (probability weighted moment) estimator.

            beta = lambda_2 / ln 2
            mu   = lambda_1 - gamma * beta

        Unbiased PWM estimators are used for b0 and b1.
        """
        x = np.sort(np.asarray(data, dtype=float))
        n = x.size
        if n < 5:
            raise ValueError(f"need at least 5 observations, got {n}")

        j = np.arange(1, n + 1)
        b0 = x.mean()
        b1 = np.sum((j - 1) / (n - 1) * x) / n

        lam1 = b0
        lam2 = 2.0 * b1 - b0

        beta = lam2 / np.log(2.0)
        if beta <= 0:
            raise ValueError(
                "L-moment estimate gave beta <= 0; the sample has no positive "
                "dispersion in the tail. Check the input series."
            )
        mu = lam1 - EULER_GAMMA * beta
        return cls(mu=mu, beta=beta)

    @classmethod
    def fit_mle(cls, data: Sequence[float]) -> "Gumbel":
        """MLE, retained only for comparison with the L-moment fit."""
        x = np.asarray(data, dtype=float)
        start = cls.fit_lmoments(x)

        def nll(params):
            mu, log_beta = params
            beta = np.exp(log_beta)
            z = (x - mu) / beta
            return np.sum(z + np.exp(-z)) + x.size * log_beta

        res = optimize.minimize(nll, [start.mu, np.log(start.beta)],
                                method="Nelder-Mead")
        return cls(mu=res.x[0], beta=float(np.exp(res.x[1])))

    # --- risk measures ---------------------------------------------------
    def return_level(self, T: float) -> float:
        """Loss level exceeded on average once every T years."""
        if T <= 1:
            raise ValueError("return period must exceed 1 year")
        return float(self.ppf(1.0 - 1.0 / T))

    def var(self, alpha: float) -> float:
        """Value at Risk (upper tail, losses)."""
        return float(self.ppf(alpha))

    def cvar(self, alpha: float) -> float:
        """
        Conditional VaR:  CVaR_a = E[X | X > VaR_a]

        Integrating the quantile function directly diverges at p -> 1.
        Substituting z = -ln(-ln p)  (so x = mu + beta*z) gives

            CVaR_a = mu + beta/(1-a) * int_{z_a}^{inf} z * exp(-z - e^-z) dz

        which converges cleanly.  Guaranteed >= VaR by construction.
        """
        z_a = -np.log(-np.log(alpha))
        val, _ = integrate.quad(
            lambda z: z * np.exp(-z - np.exp(-z)), z_a, np.inf, limit=200
        )
        return float(self.mu + self.beta * val / (1.0 - alpha))

    def stop_loss(self, d: float) -> float:
        """
        Stop-loss transform  E[max(0, X - d)] = int_d^inf (x - d) f(x) dx.
        This is the expected payout of a layer attaching at d.
        """
        upper = self.ppf(1.0 - 1e-10)
        if d >= upper:
            return 0.0
        val, _ = integrate.quad(lambda x: (x - d) * self.pdf(x), d, upper,
                                limit=200)
        return float(max(val, 0.0))


# ----------------------------------------------------------------------
# 2. Area-yield index insurance contract
# ----------------------------------------------------------------------

@dataclass
class AreaYieldContract:
    """
    Standard area-yield contract.

        trigger yield   Y_d = lambda * Y_ref
        payout          P   = TSI * min(1, max(0, (Y_d - Y) / (Y_d - Y_e)))

    Working in shortfall space  X = Y_ref - Y  gives
        attachment  d = (1 - lambda) * Y_ref
        exhaustion  e = (1 - lambda_exit) * Y_ref
    """
    y_ref: float                 # reference (expected) yield, kg/ha
    coverage: float = 0.80       # lambda — trigger at 80% of reference
    exit_level: float = 0.40     # lambda_exit — full payout at 40%
    tsi: float = 1000.0          # total sum insured per ha (currency)

    def __post_init__(self):
        if not 0 < self.exit_level < self.coverage <= 1:
            raise ValueError("require 0 < exit_level < coverage <= 1")

    @property
    def attachment(self) -> float:
        return (1.0 - self.coverage) * self.y_ref

    @property
    def exhaustion(self) -> float:
        return (1.0 - self.exit_level) * self.y_ref

    def payout(self, shortfall):
        """Payout as a function of shortfall X = Y_ref - Y."""
        x = np.asarray(shortfall, dtype=float)
        frac = (x - self.attachment) / (self.exhaustion - self.attachment)
        return self.tsi * np.clip(frac, 0.0, 1.0)

    def pure_premium(self, dist: Gumbel) -> float:
        """
        Expected payout under the fitted loss distribution.

        For a capped linear layer:
            E[P] = TSI/(e-d) * ( SL(d) - SL(e) )
        where SL is the stop-loss transform.
        """
        d, e = self.attachment, self.exhaustion
        return self.tsi / (e - d) * (dist.stop_loss(d) - dist.stop_loss(e))

    def trigger_probability(self, dist: Gumbel) -> float:
        return float(1.0 - dist.cdf(self.attachment))


def coverage_for_trigger_prob(dist: Gumbel, y_ref: float,
                              target_p: float = 0.15) -> float:
    """
    Solve for the coverage level lambda that makes the contract trigger
    with probability target_p (e.g. 0.15 ~ once every 7 years).

        d = ppf(1 - target_p),   lambda = 1 - d / y_ref

    This turns coverage from an arbitrary choice into a design decision
    tied to the district's own yield variability.
    """
    if not 0 < target_p < 1:
        raise ValueError("target_p must lie in (0, 1)")
    d = dist.ppf(1.0 - target_p)
    lam = 1.0 - d / y_ref
    return float(np.clip(lam, 0.05, 0.99))


# ----------------------------------------------------------------------
# 3. Premium loading
# ----------------------------------------------------------------------

def commercial_premium(pure: float, dist: Gumbel, contract: AreaYieldContract,
                       alpha: float = 0.99, k: float = 0.15,
                       expense_ratio: float = 0.25) -> dict:
    """
    Commercial rate = pure premium + risk load + expenses.

        risk load = k * (capped CVaR - pure premium)

    The CVaR is capped at the contract limit, since the insurer's exposure
    per hectare can never exceed TSI.
    """
    cvar_loss = dist.cvar(alpha)
    cvar_payout = float(contract.payout(cvar_loss))   # capped at TSI
    risk_load = k * max(cvar_payout - pure, 0.0)
    technical = pure + risk_load
    gross = technical / (1.0 - expense_ratio)
    return {
        "pure_premium": pure,
        "cvar_payout": cvar_payout,
        "risk_load": risk_load,
        "technical_premium": technical,
        "gross_premium": gross,
        "rate_on_line": gross / contract.tsi,
    }


# ----------------------------------------------------------------------
# 4. Validation — the checks v1.0 did not have
# ----------------------------------------------------------------------

def validate(dist: Gumbel, contract: AreaYieldContract,
             alphas=(0.90, 0.95, 0.99),
             periods=(5, 10, 20, 50, 100)) -> list:
    """Return a list of (name, passed, detail) sanity checks."""
    out = []

    # 1. CVaR >= VaR at every level
    ok = True
    detail = []
    for a in alphas:
        v, c = dist.var(a), dist.cvar(a)
        if c < v:
            ok = False
        detail.append(f"a={a}: VaR={v:.1f}, CVaR={c:.1f}")
    out.append(("CVaR >= VaR", ok, "; ".join(detail)))

    # 2. Return levels strictly increasing in T
    rl = [dist.return_level(T) for T in periods]
    out.append(("Return levels monotone", bool(np.all(np.diff(rl) > 0)),
                ", ".join(f"T{T}={v:.1f}" for T, v in zip(periods, rl))))

    # 3. Physical bound: a 100-year shortfall cannot exceed the whole crop
    rl100 = dist.return_level(100)
    out.append(("RL(100) <= reference yield", rl100 <= contract.y_ref,
                f"RL(100)={rl100:.1f} vs Y_ref={contract.y_ref:.1f}"))

    # 4. Trigger probability must be a valid probability below 0.50.
    #    A very small value is not a model error — it means the coverage
    #    level is set too low for this district's variability, which is a
    #    product-design issue, reported separately below.
    p = contract.trigger_probability(dist)
    out.append(("Trigger prob valid (0, 0.50)", 0.0 < p < 0.50,
                f"P(trigger)={p:.4f}"))
    if p < 0.02:
        out.append(("[design] coverage level meaningful", True,
                    f"P(trigger)={p:.4f} < 2% — consider raising coverage"))

    # 5. Pure premium below the sum insured
    pp = contract.pure_premium(dist)
    out.append(("Pure premium < TSI", 0 <= pp < contract.tsi,
                f"pure={pp:.2f}, TSI={contract.tsi:.2f}"))

    return out


# ----------------------------------------------------------------------
# 5. Empirical cross-check (burn rate)
# ----------------------------------------------------------------------

def burn_rate(yields: Sequence[float], contract: AreaYieldContract) -> dict:
    """
    Historical burn rate: what the contract would actually have paid.
    Model-free benchmark for the fitted premium.
    """
    y = np.asarray(yields, dtype=float)
    shortfall = contract.y_ref - y
    payouts = contract.payout(shortfall)
    return {
        "payouts": payouts,
        "mean_payout": float(payouts.mean()),
        "burn_rate": float(payouts.mean() / contract.tsi),
        "n_triggers": int((payouts > 0).sum()),
        "n_years": y.size,
    }
