import numpy as np
import sklearn.cluster
from fuzzywuzzy import fuzz


def distance(k1, k2):
    ratio = fuzz.token_set_ratio(k1.casefold(), k2.casefold())
    if ratio == 0:
        return 0.0
    else:
        return ratio / 100


def affinity(keyword_counts):
    results = dict()
    keywords = np.asarray(list(keyword_counts.keys()))
    total_count = sum(keyword_counts.values())
    # use the number of occurrences as a way to assign exemplar preference
    preference = np.asarray([count / total_count for count in keyword_counts.values()])
    similarity_l = [[distance(w1, w2) for w1 in keywords] for w2 in keywords]
    similarity = np.array(similarity_l)
    affprop = sklearn.cluster.AffinityPropagation(
        affinity="precomputed", damping=0.5, preference=preference
    )
    affprop.fit(similarity)
    for cluster_id in np.unique(affprop.labels_):
        exemplar = keywords[affprop.cluster_centers_indices_[cluster_id]]
        cluster = np.unique(keywords[np.nonzero(affprop.labels_ == cluster_id)])
        results[exemplar] = list(cluster)
    return results
