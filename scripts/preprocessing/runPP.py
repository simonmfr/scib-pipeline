#!/usr/bin/env python
# coding: utf-8

import scanpy as sc
import scib
import warnings
warnings.filterwarnings('ignore')


def runPP(inPath, outPath, hvg, batch, rout, scale, seurat):
    """
    params:
        inPath: path of the anndata object
        outPath: path of the preprocessed file to be written
        hvg: number of highly variable genes to use
        rout: set to true to save a Seurat object
        scale: set to true to activate scaling
        seurat: set to true to produce hvg list
    """

    adata = sc.read(inPath)
    hvgs=adata.var.index

    # remove HVG if already precomputed
    if 'highly_variable' in adata.var:
        del adata.var['highly_variable']
    
    if hvg > 500:
        print("Computing HVGs ...")
        if seurat:
            hvgs= scib.preprocessing.hvg_batch(adata,batch_key=batch, target_genes=hvg, adataOut=False)
        else:
            adata = scib.preprocessing.hvg_batch(adata,
                                                batch_key=batch,
                                                target_genes=hvg,
                                                adataOut=True)
    if scale:
        print("Scaling data ...")
        adata = scib.preprocessing.scale_batch(adata, batch)
        
    if rout:
        print("Save as RDS")
        scib.preprocessing.saveSeurat(adata, outPath, batch, hvgs)
        
    else:
        print("Save as HDF5")
        sc.write(outPath, adata)


if __name__=='__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Run the integration methods')

    parser.add_argument('-i', '--input_file', required=True)
    parser.add_argument('-o', '--output_file', required=True)
    parser.add_argument('-b', '--batch', required=True, help='Batch variable')
    parser.add_argument('-v', '--hvgs', help='Number of highly variable genes', default=2000)
    parser.add_argument('-r', '--rout', help='Save output for R methods', action='store_true')
    parser.add_argument('-s', '--scale', action='store_true', help='Scale the data per batch')
    parser.add_argument('-l', '--seurat', help='Generate output for seurat including hvg list', action='store_true')

    args = parser.parse_args()
    file = args.input_file
    out = args.output_file
    batch = args.batch
    hvg = int(args.hvgs)
    rout = args.rout
    seurat = args.seurat
    scale = args.scale
    
    runPP(file, out, hvg, batch, rout, scale, seurat)
