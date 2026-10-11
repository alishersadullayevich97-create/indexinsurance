"""5-8-bosqichlar. Ekstremal qiymatlar nazariyasi, bootstrap va risk o'lchovlari.

Dissertatsiyaning 2.3-bo'limi. Muhim uslubiy nuqta: GEV taqsimotining
shakl parametri kichik tanlanmada baholanmaydi, shu sababli Gumbel
spetsifikatsiyasi tanlanadi. Bu qaror empirik tarzda tekshiriladi.
"""
import numpy as np
import pandas as pd
from scipy import stats, integrate, optimize
from config import N_BOOTSTRAP, RANDOM_SEED


def loss_series(anomaly_abs):
    """Yo'qotish qatori: trenddan pastga og'ish (musbat qiymat = yo'qotish)."""
    return -np.asarray(anomaly_abs, dtype=float)


def fit_gumbel(losses):
    mu, sigma = stats.gumbel_r.fit(losses)
    return {"mu": mu, "sigma": sigma, "dist": stats.gumbel_r(loc=mu, scale=sigma)}


def check_gev_stability(losses, n_boot=N_BOOTSTRAP, seed=RANDOM_SEED):
    """GEV shakl parametrining baholanish barqarorligini tekshiradi.

    Ishonch oralig'i nolni va ikkala ishorani ham o'z ichiga olsa,
    parametr ma'lumot asosida aniqlanmagan hisoblanadi.
    """
    rng = np.random.default_rng(seed)
    shape, loc, scale = stats.genextreme.fit(losses)
    xis = []
    for _ in range(n_boot):
        s = rng.choice(losses, size=len(losses), replace=True)
        try:
            sh, _, _ = stats.genextreme.fit(s)
            xis.append(-sh)
        except Exception:
            pass
    xis = np.array(xis)
    lo, hi = np.percentile(xis, [2.5, 97.5])
    return {"xi": -shape, "scale": scale, "ci_low": lo, "ci_high": hi,
            "identified": not (lo < 0 < hi)}


def gev_profile_likelihood(losses, xi_min=-0.6, xi_max=1.2, step=0.02, level=0.95):
    """GEV shakl parametrining profil ehtimolligi (v1.1.0; dissertatsiya 2.3.1, 2-ilova).

    Har bir xi uchun mu va sigma ehtimollik bo'yicha optimallashtiriladi.
    Natija: profil bahosi xi, chi-kvadrat(1) asosidagi ishonch oralig'i va
    Gumbel (xi = 0) modeliga nisbatan ehtimollik nisbati testi. Kichik tanlanmada
    erkin GEV bahosi buzilgan yechimga (sigma -> 0) tushishi mumkin; profil
    ehtimollik bu holatdan xoli.
    """
    x = np.asarray(losses, dtype=float)
    n = len(x)
    mu_g, s_g = stats.gumbel_r.fit(x)

    def nll(p, xi):
        mu, ls = p
        z = (x - mu) / np.exp(ls)
        if abs(xi) < 1e-8:
            return n * ls + z.sum() + np.exp(-z).sum()
        t = 1 + xi * z
        if np.any(t <= 0):
            return 1e12
        return n * ls + (1 + 1 / xi) * np.log(t).sum() + (t ** (-1 / xi)).sum()

    cache = {}

    def prof(xi, warm=None):
        key = round(float(xi), 10)
        if key not in cache:
            starts = [np.array([mu_g, np.log(s_g)])] + ([warm] if warm is not None else [])
            best = min((optimize.minimize(nll, st, args=(xi,), method="Nelder-Mead",
                                          options={"xatol": 1e-7, "fatol": 1e-9, "maxiter": 4000})
                        for st in starts), key=lambda r: r.fun)
            cache[key] = (-float(best.fun), best.x)
        return cache[key]

    grid = np.round(np.arange(xi_min, xi_max + step / 2, step), 6)
    ll = np.empty(len(grid))
    i0 = int(np.argmin(np.abs(grid)))
    for order in (range(i0, len(grid)), range(i0, -1, -1)):   # xi = 0 dan ikki tomonga, iliq start
        warm = None
        for i in order:
            ll[i], warm = prof(grid[i], warm)
    i = int(ll.argmax())
    r = optimize.minimize_scalar(lambda v: -prof(v)[0], method="bounded",
                                 bounds=(grid[max(i - 1, 0)], grid[min(i + 1, len(grid) - 1)]),
                                 options={"xatol": 1e-5})
    xi_hat, ll_hat = float(r.x), float(-r.fun)
    ll_gum = prof(0.0)[0]
    lr = max(0.0, 2 * (ll_hat - ll_gum))
    cut = ll_hat - stats.chi2.ppf(level, 1) / 2
    inside = grid[ll >= cut]
    f = lambda v: prof(v)[0] - cut
    lo = optimize.brentq(f, inside.min() - step, xi_hat, xtol=1e-5)
    hi = optimize.brentq(f, xi_hat, inside.max() + step, xtol=1e-5)
    return {"xi": round(xi_hat, 3), "ci_low": round(float(lo), 3), "ci_high": round(float(hi), 3),
            "ll_gev": round(ll_hat, 2), "ll_gumbel": round(ll_gum, 2),
            "LR": round(lr, 3), "p": round(float(stats.chi2.sf(lr, 1)), 3)}


def return_levels(dist, periods=(10, 20, 50, 100), mean_production=None):
    """T yillik qaytarilish darajalari: x_T = mu - sigma*ln(-ln(1-1/T))."""
    rows = []
    for T in periods:
        q = dist.ppf(1 - 1 / T)
        row = {"qaytarilish_davri": T, "yoqotish_t": round(q, 0)}
        if mean_production:
            row["yoqotish_pct"] = round(q / mean_production * 100, 1)
        rows.append(row)
    return pd.DataFrame(rows)


def bootstrap_return_levels(losses, periods=(10, 20, 50, 100),
                            mean_production=None, n_boot=N_BOOTSTRAP, seed=RANDOM_SEED):
    """Qaytarilish darajalarining 95% ishonch oraliqlari."""
    rng = np.random.default_rng(seed)
    acc = {T: [] for T in periods}
    for _ in range(n_boot):
        s = rng.choice(losses, size=len(losses), replace=True)
        try:
            mu, sg = stats.gumbel_r.fit(s)
            d = stats.gumbel_r(loc=mu, scale=sg)
            for T in periods:
                v = d.ppf(1 - 1 / T)
                acc[T].append(v / mean_production * 100 if mean_production else v)
        except Exception:
            pass
    base = fit_gumbel(losses)["dist"]
    rows = []
    for T in periods:
        a = np.array(acc[T])
        pt = base.ppf(1 - 1 / T)
        rows.append({"qaytarilish_davri": T,
                     "nuqtaviy": round(pt / mean_production * 100 if mean_production else pt, 1),
                     "quyi_2.5": round(np.percentile(a, 2.5), 1),
                     "yuqori_97.5": round(np.percentile(a, 97.5), 1)})
    return pd.DataFrame(rows)


def var_cvar(dist, alphas=(0.95, 0.99), mean_production=None):
    """VaR - kvantil; CVaR - undan oshgan yo'qotishlarning shartli kutilmasi."""
    rows = []
    for a in alphas:
        var = dist.ppf(a)
        cv, _ = integrate.quad(lambda q: dist.ppf(q), a, 0.999999, limit=200)
        cvar = cv / (1 - a)
        row = {"ishonch": a, "VaR_t": round(var, 0), "CVaR_t": round(cvar, 0)}
        if mean_production:
            row["VaR_pct"] = round(var / mean_production * 100, 1)
            row["CVaR_pct"] = round(cvar / mean_production * 100, 1)
        rows.append(row)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    from s01_data import load_province
    from s02_detrend import detrend_series
    v = load_province()
    res = detrend_series(v.year, v.production_t)
    L = loss_series(res["anomaly_abs"]); mp = v.production_t.mean()
    g = fit_gumbel(L)
    print(f"Gumbel: mu = {g['mu']:,.0f}, sigma = {g['sigma']:,.0f}\n")
    gev = check_gev_stability(L)
    print(f"GEV shakl xi = {gev['xi']:+.3f}, 95% CI = [{gev['ci_low']:+.2f}, {gev['ci_high']:+.2f}]")
    print(f"Parametr aniqlanganmi: {'ha' if gev['identified'] else 'YOQ -> Gumbel tanlanadi'}\n")
    pl = gev_profile_likelihood(L)
    print(f"Profil ehtimollik: xi = {pl['xi']:+.3f}, 95% CI = [{pl['ci_low']:+.3f}, {pl['ci_high']:+.3f}], "
          f"LR = {pl['LR']:.3f} (p = {pl['p']:.3f})\n")
    print(return_levels(g["dist"], mean_production=mp).to_string(index=False))
    print()
    print(var_cvar(g["dist"], mean_production=mp).to_string(index=False))
    print()
    print(bootstrap_return_levels(L, mean_production=mp).to_string(index=False))
