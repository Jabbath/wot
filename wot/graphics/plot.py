# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
from matplotlib import patches
from matplotlib import pyplot as plt

import wot.graphics


def __make_figure(y=1, x=1, projection=None):
    plt.clf()
    return plt.subplots(y, x, figsize=(8 * x, 6 * y), projection=None)


def legend_figure(figure, legend_list, loc=0):
    patch_list = [patches.Patch(color=c, label=l) for c, l in legend_list]
    figure.legend(handles=patch_list, loc=loc)


def interpolate(x, xi, yi, sigma):
    val = x - xi
    val *= -val
    diff = val
    sigma2 = 2 * sigma ** 2
    w = np.exp(diff / sigma2)
    fx = (yi * w).sum()
    return fx / w.sum()


def kernel_smooth(xi, yi, start, stop, steps, sigma):
    xlist = np.linspace(start, stop, steps)
    fhat = np.zeros(len(xlist))
    for i in range(len(xlist)):
        fhat[i] = interpolate(xlist[i], xi, yi, sigma)
    return xlist, fhat


ot_validation_legend = {
    'P': ["#e41a1c", "between real batches"],
    'I': ["#377eb8", "between interpolated and real"],
    'F': ["#4daf4a", "between first and real"],
    'L': ["#984ea3", "between last and real"],
    'R': ["#ff7f00", "between random (no growth) and real"],
    'Rg': ["#ffff33", "between random (with growth) and real"],
    'A': ["#bdbdbd", "between first and last"],
    'I1': ["#a6cee3", "between first and interpolated"],
    'I2': ["#fb9a99", "between last and interpolated"]
}


def plot_ot_validation_ratio(df, filename):
    # (interpolated - real) / (null - real)
    df = df.reset_index()
    df = df.sort_values('interval_mid')

    interpolated_df = df[df['name'] == 'I']
    null_growth = df[df['name'] == 'Rg']
    null_no_growth = df[df['name'] == 'R']
    if (interpolated_df['interval_mid'].values - null_growth['interval_mid'].values).sum() != 0:
        raise ValueError('Timepoints are not aligned')
    if (interpolated_df['interval_mid'].values - null_no_growth['interval_mid'].values).sum() != 0:
        raise ValueError('Timepoints are not aligned')

    plt.figure(figsize=(10, 10))
    with_growth_score = (interpolated_df['mean'].values / null_growth['mean'].values).sum()
    no_growth_score = (interpolated_df['mean'].values / null_no_growth['mean'].values).sum()
    plt.title(
        "OT Validation: \u03A3(interpolated - real)/(null - real), with growth={:.2f}, no growth={:.2f}".format(
            with_growth_score, no_growth_score))
    plt.xlabel("time")
    plt.ylabel("ratio")

    plt.plot(interpolated_df['interval_mid'], interpolated_df['mean'].values / null_growth['mean'].values,
             label='with growth')
    plt.plot(interpolated_df['interval_mid'], interpolated_df['mean'].values / null_no_growth['mean'].values,
             label='no growth')
    plt.legend()
    plt.savefig(filename)


def plot_ot_validation_summary_stats(df, bandwidth=None):
    df = df.reset_index()
    plt.figure(figsize=(10, 10))
    plt.title("OT Validation")
    plt.xlabel("time")
    plt.ylabel("distance")
    legend = {}

    for p, d in df.groupby('name'):
        if p not in ot_validation_legend.keys():
            continue
        t = np.asarray(d['interval_mid'])
        m = np.asarray(d['mean'])
        s = np.asarray(d['std'])
        legend[p] = ot_validation_legend[p]
        if bandwidth is not None:
            x, m = kernel_smooth(t, m, 0, t[len(t) - 1], 1000, bandwidth)
            x, s = kernel_smooth(t, s, 0, t[len(t) - 1], 1000, bandwidth)
            t = x
        plt.plot(t, m, '-o', color=ot_validation_legend[p][0])
        plt.fill_between(t, m - s, m + s, color=ot_validation_legend[p][0], alpha=0.2)
    wot.graphics.legend_figure(plt, legend.values())

def plot_triangle(fates_ds, day, name1, name2, filename=None):
    """
    Plots cells in barycentric coordinates (2D) according to their fates.
    Cells are placed by using the fates to generate a convex combination
    of the triangle's vertices.
    
    Parameters
    ----------
    fates_ds: pandas.DataFrame
        A df of cell fates as generated by wot.tmap.TransportMapModel.fates.
    day: float
        The timepoint from which we want to plot cells.
    name1: str
        The cell population whose fate will the first of the triangle's vertices.
    name2: str
        The cell population whose fate will the second of the triangle's vertices.
    filename: str, optional
        The name of the file to save the plot as. None to skip saving.
    """
    
    figure = plt.figure(figsize=(10, 10))   
    
    #Get the fates for our two cell populations
    fate1 = fate_ds[:,name1][fate_ds.obs['day']==day].X.flatten()
    fate2 = fate_ds[:,name2][fate_ds.obs['day']==day].X.flatten()
    
    #Take a convex combination of the triangle's vertices using the fates
    Nrows = len(fate1)
    x = np.zeros(Nrows)
    y = np.zeros(Nrows)
    P = np.array([[1,0],[np.cos(2*math.pi/3),math.sin(2*math.pi/3)],[math.cos(4*math.pi/3),math.sin(4*math.pi/3)]])

    for i in range(0,Nrows):
        ff = np.array([fate1[i],fate2[i],1-(fate1[i]+fate2[i])])
        x[i] = (ff @ P)[0]
        y[i] = (ff @ P)[1]
    
    #Plot the triangle
    t1 = plt.Polygon(P, color=(0,0,0,0.1))
    plt.gca().add_patch(t1)
    
    #Plot the vertices
    vx = P[:,0]
    vy = P[:,1]
    plt.scatter(vx,vy)
    
    #Plot cells and labels
    plt.scatter(x,y)
    plt.text(P[0,0]+.1, P[0,1], name1)
    plt.text(P[1,0]-.1, P[1,1]+.1, name2)
    plt.text(P[2,0]-.1, P[2,1]-.2, 'Other')
    plt.axis('equal')
    plt.axis('off')
    
    plt.title('{} vs. {} on day {}'.format(name1, name2, day))
    
    #Optionally save the figure
    if filename is not None:
        plt.savefig(filename)
        
def plot_log_odds(fate_ds, name1, name2, filename=None):
    """
    Displays log-odds for a pair of fates. This is the log of the 
    ratio of fate probabilities.
    
    Parameters
    ----------
    fates_ds: pandas.DataFrame
        A df of cell fates as generated by wot.tmap.TransportMapModel.fates.
    name1: str
        The cell population whose fate will the numerator.
    name2: str
        The cell population whose fate will denominator.
    filename: str, optional
        The name of the file to save the plot as. None to skip saving.
    """
    figure = plt.figure(figsize=(10, 10))
    
    #Extract the fate probabilities for the two cell populations
    fate1 = fate_ds[:, name1].X
    fate2 = fate_ds[:, name2].X
    
    #Calculate the log odds
    p = np.log(1e-9 + np.divide(fate1, fate2, out=np.zeros_like(fate1), where=fate2 != 0))
    
    #Plot log-odds by day
    plt.scatter(fate_ds.obs['day'], p, s=4, marker=',')
    plt.xlabel('Day')
    plt.ylabel('Log Odds')
    plt.title('{} vs. {}'.format(name1, name2))
    
    #Optionally save the figure
    if filename is not None:
        plt.savefig(filename)