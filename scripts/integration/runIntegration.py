#!/usr/bin/env python
# coding: utf-8

import scanpy as sc
import scib
import warnings
warnings.filterwarnings('ignore')


def runIntegration(inPath, outPath, method, hvg, batch, celltype=None):
    """
    params:
        method: name of method
        batch: name of `adata.obs` column of the batch
        max_genes_hvg: maximum number of HVG
    """

    adata = sc.read(inPath)
    
    if timing:
        if celltype is not None:
            integrated_tmp = scib.metrics.measureTM(method, adata, batch, celltype)
        else:
            integrated_tmp = scib.metrics.measureTM(method, adata, batch)            

        integrated = integrated_tmp[2][0]


        integrated.uns['mem'] = integrated_tmp[0]
        integrated.uns['runtime'] = integrated_tmp[1]

    else:
        if celltype is not None:
            integrated = method(adata, batch, celltype)
        else:
            integrated = method(adata, batch)
                
    sc.write(outPath, integrated)

if __name__=='__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Run the integration methods')

    parser.add_argument('-m', '--method', required=True)
    parser.add_argument('-i', '--input_file', required=True)
    parser.add_argument('-o', '--output_file', required=True)
    parser.add_argument('-b', '--batch', required=True, help='Batch variable')
    parser.add_argument('-v', '--hvgs', help='Number of highly variable genes', default=2000)
    parser.add_argument("-t", '--timing', help='Activate runtime and memory profiling', action='store_true')
    parser.add_argument("-c", '--celltype', help='Cell type variable', default=None)

    args = parser.parse_args()
    file = args.input_file
    out = args.output_file
    batch = args.batch
    hvg = int(args.hvgs)
    timing = args.timing
    celltype = args.celltype
    method = args.method
    methods = {
        'scanorama': scib.integration.runScanorama,
        'trvae': scib.integration.runTrVae,
        'trvaep': scib.integration.runTrVaep,
        'scgen': scib.integration.runScGen,
        'mnn': scib.integration.runMNN,
        'bbknn': scib.integration.runBBKNN,
        'scvi': scib.integration.runScvi,
        'scanvi': scib.integration.runScanvi,
        'combat': scib.integration.runCombat,
        'saucie': scib.integration.runSaucie,
        'desc': scib.integration.runDESC
    }
    
    if method not in methods.keys():
        raise ValueError(f'Method "{method}" does not exist. Please use one of '
                         f'the following:\n{list(methods.keys())}')
    
    run= methods[method]
    runIntegration(file, out, run, hvg, batch, celltype)
