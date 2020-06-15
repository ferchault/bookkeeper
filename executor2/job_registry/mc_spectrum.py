#!/usr/bin/env python
# %%
import numpy as np
import numba

# meta parameters
LINEWIDTH = 0.3
EXPERIMENT_UNCERTAIN_SCALE = 10

# reference data
grid_short = np.array([ 0.138912671079212, 0.136826895237182, 0.134802828739590, 0.132837772927060, 0.130929184235579, 0.129074663212412, 0.127271944452462, 0.125518887366340, 0.123813467701037, 0.122153769742578, 0.120537979137517, 0.118964376276714, 0.117431330190674, 0.115937292910894, 0.114480794256235, 0.113060437007398, 0.111674892436229, 0.110322896159762, 0.109003244291822, 0.107714789867569, 0.106456439518648, 0.105227150378710, 0.104025927200871, 0.102851819670387, 0.101703919897280, 0.100581360075014, 0.099483310292536, 0.098408976488081, 0.097357598534149])
experiment_short = np.array([16062.12376,16022.67847,14294.97459,13537.62494,11707.36329,8788.411529,6153.465882,3234.514118,2193.158353,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0])
mae = np.array((0.009367729738238392, 0.007644026369760024, 0.006634207502480805, 0.03514044031325359, 0.037518177682891826, 0.035671701408550395))

# Definition of spectrum
@numba.jit(nopython=True)
def spectrum(values):
    sigma_inv=1/(LINEWIDTH*0.036749304951208)
    const=16836.70285
    dec=0.4342944819032518
    return const*dec*(0.05746523219) * sigma_inv*(values[3]*np.exp(-0.5* ((grid_short-values[0]) * sigma_inv) ** 2) +values[4]*np.exp(-0.5* ((grid_short-values[1]) * sigma_inv) ** 2) +values[5]*np.exp(-0.5* ((grid_short-values[2]) * sigma_inv) ** 2))

# %%
upper_limit = spectrum((0.145, 1, 1, 0.5, 0, 0)) 
upper_limit = np.maximum(upper_limit, experiment_short + 300)
#upper_limit = np.maximum(upper_limit, experiment_short * 2)
upper_limit[:10] += 4000

lower_limit = experiment_short 
lower_limit = np.minimum(lower_limit, experiment_short - 4000)
lower_limit = np.maximum(lower_limit, 0)

# %%
def draw_random_from_molecular_distribution(centers, mae, N):
    sigma = mae / np.sqrt(2/np.pi)    

    # random oscillator strengths
    osz1 = np.random.normal(centers[3], sigma[3], N)
    osz1 = osz1[osz1 > 0]
    osz2 = np.random.normal(centers[4], sigma[4], len(osz1))
    osz2 = osz2[osz2 > 0]
    osz3 = np.random.normal(centers[5], sigma[5], len(osz2))
    osz3 = osz3[osz3 > 0]

    # trim length
    N = len(osz3)
    osz1 = osz1[:N]
    osz2 = osz2[:N]

    # matching energies
    S1 = np.random.normal(centers[0], sigma[0], N)
    S2 = np.random.normal(centers[1], sigma[1], N)
    S3 = np.random.normal(centers[2], sigma[2], N)

    # glue
    return np.vstack((S1, S2, S3, osz1, osz2, osz3))

def monte_carlo_probability(candidate, N):
    candidates = draw_random_from_molecular_distribution(candidate, mae, N).T
    success = 0
    trials = 0
    tmax = max(experiment_short)
    for candidate in candidates:
        s = spectrum(candidate)
        trials += 1
        rescale = max(s) / tmax
        if rescale > EXPERIMENT_UNCERTAIN_SCALE or rescale < 1/EXPERIMENT_UNCERTAIN_SCALE:
            continue
        s /= rescale
        if np.all(s >= lower_limit) and np.all(s <= upper_limit):
            success += 1
    return success / N


# %%
class Task:
	def __init__(self, connection):
		pass

	def run(self, commandstring):
		try:
			dbg = [float(_) for _ in commandstring.split(",")]
			probability = str(monte_carlo_probability(dbg, 10000))
		except:
			probability = "--"		
		return probability, 0

