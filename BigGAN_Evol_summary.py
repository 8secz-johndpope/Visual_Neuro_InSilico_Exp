import os
import re
import numpy as np
import matplotlib.pylab as plt
from time import time
from os.path import join
import pandas as pd
from scipy.stats import ttest_rel,ttest_ind
#%% summarize difference between methods when applying to fc6
rootdir = r"E:\OneDrive - Washington University in St. Louis\BigGAN_Optim_Tune"
summarydir = join(rootdir, "summary")
os.makedirs(summarydir, exist_ok=True)
# savedir = r"E:\OneDrive - Washington University in St. Louis\BigGAN_Optim_Tune\%s_%s_%d"
#%% Do a survey of all the exp done
unit_strs = os.listdir(rootdir)
unit_strs = [unit_str for unit_str in unit_strs if "alexnet" in unit_str]
unit_pat = re.compile("(.*)_(.*)_(\d*)")
unit_tups = [unit_pat.findall(unit_str)[0] for unit_str in unit_strs]
unit_tups = [(tup[0],tup[1],int(tup[2])) for tup in unit_tups]
rec_col = []
for ui, unit_str in enumerate(unit_strs):
    unit_tup = unit_tups[ui]
    fns = os.listdir(join(rootdir, unit_str))
    assert unit_str == "%s_%s_%d"%unit_tup
    trajfns = [fn for fn in fns if "traj" in fn]
    traj_fn_pat = re.compile("traj(.*)_(\d*)_score([\d.-]*).jpg")
    for trajfn in trajfns:
        parts = traj_fn_pat.findall(trajfn)[0]
        entry = (unit_str, *unit_tup, parts[0], int(parts[1]), float(parts[2]))
        rec_col.append(entry)

exprec_tab = pd.DataFrame(rec_col, columns=["unitstr", 'net', 'layer', 'unit', "optimizer", "RND", "score"])
#%%
exprec_tab.to_csv(join(rootdir, "optim_raw_score_tab.csv"))
#%% Align the experiments with same initialization
align_col = []
methods = exprec_tab.optimizer.unique()
for ui, unit_str in enumerate(unit_strs):
    unit_tup = unit_tups[ui]
    mask = exprec_tab.unitstr == unit_str
    RNDs = exprec_tab[mask].RND.unique()
    for RND in RNDs:
        entry = [unit_str, *unit_tup, RND, ]
        for method in methods:
            maskprm = mask & (exprec_tab.RND==RND) & (exprec_tab.optimizer==method)
            try:
                score = exprec_tab[maskprm].score.item()
            except ValueError:
                print("Imcomplete Entry %s (RND %d, unit %s)" % (method, RND, unit_str))
                score = np.nan
            entry.append(score)
        align_col.append(tuple(entry))
align_tab = pd.DataFrame(align_col, columns=["unitstr", "net", "layer", "unit", "RND"]+list(methods))
#%%
align_tab.to_csv(join(rootdir, "optim_aligned_score_tab.csv"))
#%%
ttest_rel(exprec_tab[exprec_tab.optimizer=="CMA_class"].score,
    exprec_tab[exprec_tab.optimizer=="CMA_prod"].score)
#%%
ttest_rel(align_tab.CholCMA, align_tab.CMA_all, nan_policy='omit')
ttest_ind(align_tab.CholCMA, align_tab.CMA_all, nan_policy='omit')
ttest_rel(align_tab.CholCMA, align_tab.CholCMA_noA, nan_policy='omit')
ttest_ind(align_tab.CholCMA, align_tab.CholCMA_noA, nan_policy='omit')
#%%

jitter = 0.1*np.random.randn(align_tab.shape[0])
plt.figure(figsize=[8,8])
plt.plot(np.array([[1, 2, 3, 4,5]]).T+jitter[np.newaxis, :], align_tab[["CholCMA","CholCMA_noA","CMA_all","CMA_class",
                                                           "CMA_prod",]].to_numpy().T, color="gray", alpha=0.5)
plt.scatter(1+jitter, align_tab.CholCMA, label="CholCMA")
plt.scatter(2+jitter, align_tab.CholCMA_noA, label="CholCMA_noA")
plt.scatter(3+jitter, align_tab.CMA_all, label="CMA_all")
plt.scatter(4+jitter, align_tab.CMA_class, label="CMA_class")
plt.scatter(5+jitter, align_tab.CMA_prod, label="CMA_prod")
plt.ylabel("Activation Score")
plt.xlabel("Optimizer Used")
plt.xticks([1,2,3,4,5],["CholCMA","CholCMA_noA","CMA_all","CMA_class","CMA_prod"])
chol_all_t = ttest_rel(align_tab.CholCMA, align_tab.CMA_all, nan_policy='omit')
chol_prod_t = ttest_rel(align_tab.CholCMA, align_tab.CMA_prod, nan_policy='omit')
chol_class_t = ttest_rel(align_tab.CholCMA, align_tab.CMA_class, nan_policy='omit')
chol_noA_t = ttest_rel(align_tab.CholCMA, align_tab.CholCMA_noA, nan_policy='omit')
plt.title("Comparing Performance of Optimizers in Activation Maximizing Alexnet units\n"
          "paired-t: CholCMA-CMA_all:t=%.1f(p=%.1E)\nCholCMA-CMA_prod:t=%.1f(p=%.1E)\n CholCMA-CMA_class:t=%.1f("
          "p=%.1E) \nCholCMA-CholCMA_noA:t=%.1f(p=%.1E)"%
          (chol_all_t.statistic, chol_all_t.pvalue,chol_prod_t.statistic, chol_prod_t.pvalue,chol_class_t.statistic,
            chol_class_t.pvalue,chol_noA_t.statistic, chol_noA_t.pvalue,))
plt.axis('auto')
plt.savefig(join(summarydir, "fc6_optimizer_scores_cmp.jpg"))
plt.show()
