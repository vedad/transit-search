#!/usr/bin/env python

import numpy as np
from astropy.constants import R_sun, M_sun, G
import astropy.units as u
from numpy import pi, sqrt

OVERSAMPLING_FACTOR = 2
N_TRANSITS_MIN = 2
MINIMUM_PERIOD_GRID_SIZE = 100

def _frequency_grid_NAC(N_opt, A, C):
    X = np.arange(N_opt) + 1
    return (A / 3 * X + C) ** 3

# def _get_frequency_grid(f_min, f_max, A):

#     C = f_min ** (1.0 / 3) - A / 3.0
#     N_opt = (f_max ** (1.0 / 3) - f_min ** (1.0 / 3) + A / 3) * 3 / A
#     X = np.arange(N_opt) + 1
#     f_x = (A / 3 * X + C) ** 3

#     # sve N_opt, C, A

#     return f_x

def frequency_grid(
    R_star,
    M_star,
    time_span,
    period_min=0.5,
    period_max=float("inf"),
    oversampling_factor=OVERSAMPLING_FACTOR,
    n_transits_min=N_TRANSITS_MIN,
):
    """Returns array of optimal sampling periods for transit search in light curves
       Following Ofir (2014, A&A, 561, A138)"""

    if R_star < 0.01:
        text = (
            "Warning: R_star was set to 0.01 for period_grid (was unphysical: "
            + str(R_star)
            + ")"
        )
        warnings.warn(text)
        R_star = 0.1

    if R_star > 10000:
        text = (
            "Warning: R_star was set to 10000 for period_grid (was unphysical: "
            + str(R_star)
            + ")"
        )
        warnings.warn(text)
        R_star = 10000

    if M_star < 0.01:
        text = (
            "Warning: M_star was set to 0.01 for period_grid (was unphysical: "
            + str(M_star)
            + ")"
        )
        warnings.warn(text)
        M_star = 0.01

    if M_star > 1000:
        text = (
            "Warning: M_star was set to 1000 for period_grid (was unphysical: "
            + str(M_star)
            + ")"
        )
        warnings.warn(text)
        M_star = 1000

    R_star = R_star * R_sun.value
    M_star = M_star * M_sun.value
    # time_span = (time_span * u.day).to(u.s).value  # seconds

    # boundary conditions
    f_min = n_transits_min / time_span
    f_max = 1.0 / (2 * pi) * sqrt(G.to("m3 / (kg d2)").value * M_star / (3 * R_star) ** 3)

    # optimal frequency sampling, Equations (5), (6), (7)
    A = (
        (2 * pi) ** (2.0 / 3)
        / pi
        * R_star
        / (G.to("m3 / (kg d2)").value * M_star) ** (1.0 / 3)
        / (time_span * oversampling_factor)
    )

    # f_x = _get_frequency_grid(f_min, f_max, A)
    C = f_min ** (1.0 / 3) - A / 3.0
    N_opt = (f_max ** (1.0 / 3) - f_min ** (1.0 / 3) + A / 3) * 3 / A
    f_x = _frequency_grid_NAC(N_opt, A, C)

    freq_params = dict(
        N_opt = N_opt,
        A = A,
        C = C
    )

    # X = np.arange(N_opt) + 1
    # f_x = (A / 3 * X + C) ** 3
    periods = 1 / f_x

    # Cut to given (optional) selection of periods
    # periods = (P_x * u.s).to(u.day).value
    # periods = P_x
    selected_index = np.where(
        np.logical_and(periods > period_min, periods <= period_max)
    )

    number_of_periods = np.size(periods[selected_index])

    if number_of_periods > 10 ** 6:
        text = (
            "period_grid generates a very large grid ("
            + str(number_of_periods)
            + "). Recommend to check physical plausibility for stellar mass, radius, and time series duration."
        )
        warnings.warn(text)

    if number_of_periods < MINIMUM_PERIOD_GRID_SIZE:
        if time_span < 5 * 86400:
            time_span = 5 * 86400
        warnings.warn(
            "period_grid defaults to R_star=1 and M_star=1 as given density yielded grid with too few values"
        )
        return frequency_grid(
            R_star=1.0, M_star=1.0,
            time_span=time_span
            # time_span=(time_span*u.s).to(u.day).value
        )
    else:
        freqs = 1/periods[selected_index]
        freq_params["f_min"] = freqs.min()
        freq_params["f_max"] = freqs.max()

        return freqs, freq_params
        # return (f_x*1/u.s).to(1/u.day).value[selected_index], freq_params  # frequencies in 1/day
    
if __name__ == "__main__":
    f_x = frequency_grid(R_star=1, M_star=1, time_span=27)

    print(len(f_x), f_x, 1/f_x[0])