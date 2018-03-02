#!/usr/bin/env python
# -*- coding: utf-8 -*-


import wot.ot
import pandas as pd
import csv

parser = wot.ot.OptimalTransportHelper.create_base_parser('Compute transport maps between pairs of time points')
parser.add_argument('--compress', action='store_true', help='gzip output files')
parser.add_argument('--clusters', help='Two column file with cell id and cluster id')
args = parser.parse_args()
ot_helper = wot.ot.OptimalTransportHelper(args)

params_writer = None
if args.solver is 'floating_epsilon':
    params_writer = open(args.prefix + '_params.txt', 'w')
    params_writer.write('t1' + '\t' + 't2' + '\t' + 'epsilon' + '\t' + 'lambda1' + '\t' + 'lambda2'
                                                                                          '\n')

cluster_transport_maps = []
total_cluster_size = None
if args.clusters is not None:
    clusters = pd.read_table(args.clusters, index_col=0, header=None,
                             names=['cluster'], quoting=csv.QUOTE_NONE,
                             engine='python',
                             sep=None)
    clusters = clusters.align(ot_helper.gene_expression, join='right', axis=0,
                              copy=False)[0]
    grouped_by_cluster = clusters.groupby(clusters.columns[0], axis=0)
    cluster_ids = list(grouped_by_cluster.groups.keys())
    total_cluster_size = wot.ot.get_column_weights(clusters.index,
                                                   grouped_by_cluster,
                                                   cluster_ids)

column_cell_ids_by_time = []
all_cell_ids = set()


def callback(cb_args):
    result = cb_args['result']
    if args.solver is 'floating_epsilon':
        params_writer.write(
            str(cb_args['t0']) + '\t' + str(cb_args['t1']) + '\t' + str(result['epsilon']) + '\t' + str(
                result['lambda1']) + '\t' + str(
                result['lambda2']) + '\n')
    transport_map = pd.DataFrame(result['transport'], index=cb_args['p0'].index, columns=cb_args['p1'].index)
    if args.clusters is not None:
        cluster_transport_map = wot.ot.transport_map_by_cluster(
            transport_map, grouped_by_cluster, cluster_ids)
        all_cell_ids.update(transport_map.columns)
        all_cell_ids.update(transport_map.index)
        column_cell_ids_by_time.append(transport_map.columns)
        if args.verbose:
            print('Summarized transport map by cluster')
        if args.cluster_details:
            if args.verbose:
                print('Saving cluster transport map')
            cluster_transport_map.to_csv(
                args.prefix + '_cluster_' + str(cb_args['t0']) + '_' + str(cb_args['t1']) + '.txt' + (
                    '.gz' if args.compress else ''),
                index_label="id",
                sep='\t',
                compression='gzip' if args.compress
                else None)
        cluster_transport_maps.append(cluster_transport_map)

    # save the tranport map

    if args.verbose:
        print('Saving transport map')
    transport_map.to_csv(args.prefix + '_' + str(cb_args['t0']) + '_' + str(cb_args['t1']) + '.txt' + ('.gz' if
                                                                                                       args.compress else ''),
                         index_label='id',
                         sep='\t',
                         compression='gzip' if
                         args.compress else None, doublequote=False,
                         quoting=csv.QUOTE_NONE)


ot_helper.compute_transport_maps(callback)

if params_writer is not None:
    params_writer.close()

if args.clusters is not None:
    if args.verbose:
        print('Saving summarized transport map')
    weights = wot.ot.get_weights(all_cell_ids, column_cell_ids_by_time,
                                 grouped_by_cluster, cluster_ids)
    cluster_weights_by_time = weights['cluster_weights_by_time']
    combined_cluster_map = wot.ot.transport_maps_by_time(
        cluster_transport_maps,
        cluster_weights_by_time)
    combined_cluster_map.to_csv(
        args.prefix + '_cluster_summary.txt' + ('.gz' if
                                                args.compress else ''),
        index_label="id",
        sep='\t',
        compression='gzip' if args.compress
        else None)
