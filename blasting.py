# coding: utf8
# python 3.8.2
# Antoine Laporte
# Université de Bordeaux - INRAE Bordeaux
# Reconstruction de réseaux métaboliques
# Mars - Aout 2020
"""This file is the main file for the reconstruction of a draft using a previously 
made model, which has to be the most curated possible and as close as possible 
genetically speaking to the target model."""

import cobra
from os.path import join
import subprocess
import pickle
import time
import matplotlib.pyplot as plt
from statistics import mean
import copy
import re
import configparser

import graph


def save_obj(obj, path):
    """Saves the dictionary of Blastp results in a pickle file."""
    with open(path + '.pkl', 'wb+') as f:
        pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)


def load_obj(path):
    """Loads a dictionary of Blastp results stored in a pickle file."""
    with open(path + '.pkl', 'rb') as f:
        return pickle.load(f)


def read_config(ini):
    """Runs the config file containing all the information to make a new model.
    ARGS :
        ini (str) -- the path to the .ini file.
    RETURN :
        config (dict of str) -- the configuration in a python dictionary.
    """
    config = configparser.ConfigParser()
    config.read(ini)
    return config


def blast_run(WDref, WDsub, model, queryFile, subjectFile):
    """Runs multiple blasts between a subject file and each protein of the query file.
    
    ARGS : 
        model (cobra model) -- the GEM of reference.
        WDref (str) -- the path of the directory for the reference sbml model 
        and fasta file.
        WDsub (str) -- the path of the directory for the subject fasta file 
        and where the temporary proteins files will be stored.
        subjectFile (str) -- the name of the subject fasta.
        queryFile (str) -- the name of the query file.
    RETURN : 
        blast_res -- dictionary containing the result of the blastp command 
        for each gene of the model.
        Structure :
        {gene id: [res of blastp as list of value =>
        qseqid, qlen, sseqid, slen, length, nident, pident, score, evalue, bitscore]}
    """
    ###Concatenation of string to get the exact paths###
    newDir = WDsub + "Proteins_tmp/"
    queryDir = WDref + queryFile
    subjectDir = WDsub + subjectFile
    ###Creation of temporary directory containing one file per protein of the query###
    subprocess.run(["mkdir", newDir])
    print("\nCreating the individual CDS fasta files...")
    fileFasta = open(queryDir)
    queryFasta = fileFasta.read()
    ###Writing of the individual fasta files
    # Fasta name of the genes must corresponds to the IDs in the model #
    for seq in queryFasta.split(">"):
        try:
            geneName = re.search('\w+(\.\w+)*(\-\w+)*', seq).group(0)
            f = open(newDir + geneName + ".fa", "w")
            f.write(">" + seq)
            f.close()
        except AttributeError:
            print("Gene name not found in :", seq)
            pass
    fileFasta.close()
    print("...done !")
    ###End of the fasta writing
    ###Blast###
    print("\nLaunching the blast !")
    i, x = 1, len(model.genes)
    total_time = lap_time = time.time()
    blast_res = {}
    for gene in model.genes:
        if i%10==0:
            print("Protein %i out of %i\nTime : %f s" %(i,x, time.time() - lap_time))
            lap_time = time.time()
        i+=1
        requestBlast = [
            "blastp",
            "-subject",
            subjectDir,
            "-query",
            newDir + gene.id + ".fa",
            "-outfmt",
            "10 delim=, qseqid qlen sseqid slen length nident pident score evalue bitscore"]
        blast_res[gene.id] = subprocess.run(requestBlast, capture_output=True).stdout.decode('ascii').split("\n")[:-1]
    subprocess.run(["rm", "-rf", newDir])
    print("Blast done !\nTotal time : %f s" %(time.time() - total_time))
    return blast_res


def select_genes(blast_res, identity, diff, e_val, coverage, bit_score):
    """Select the subject organism's genes regarding the different treshold parameters selected.
    
    ARGS:
        blast_res -- the dictionary with the results of the blastp.
        identity -- the treshold value of identity to select the subject genes.
        diff -- the percentage of length difference tolerated between subject and query. 
        e_val -- the minimum E-Value chosen. 
        coverage -- the minimum percentage of coverage of the match.
        bit_score -- the minimum Bit-Score chosen.
    RETURN:
        dico_genes -- a dictionary with model gene as key and corresponding subject 
        key and coverage value as values.
    """
    dico_genes = {}
    for key in blast_res.keys():
        for res in blast_res[key]:
            spl = res.split(",")
            for i in range(len(spl)):
                try:
                    spl[i] = float(spl[i])
                except ValueError:
                    pass
            len_subject = spl[3]
            len_query = [spl[1] * (100 - diff) / 100, spl[1] * (100 + diff) / 100]
            min_align = coverage / 100 * spl[1]
            if spl[6] >= identity\
            and len_subject >= len_query[0]\
            and len_subject <= len_query[1]\
            and spl[4] >= min_align\
            and spl[9] >= bit_score:
                try:
                    if spl[8] <= e_val:
                        dico_genes[key].append(spl[2])
                except KeyError:
                    if spl[8] <= e_val:
                        dico_genes[key] = [spl[2]]
    return dico_genes


def drafting(model, dico_genes, model_name):
    """Creates the new COBRA model for the subject organism.
    
    ARGS:
        model -- the COBRA model used for the reconstruction.
        dico_genes -- the dictionary containing the correspondance
        between genes of the model and the subject.
        model_name -- a name for the new model (string)
    RETURN:
        new_model -- the new COBRA model automatically generated.
    """
    new_model = cobra.Model(model_name)
    #Browsing the model reactions and associating the subject's genes to them
    for reac in model.reactions:
        to_add = []
        to_search = reac.gene_reaction_rule.split(" or ")
        for gene in to_search:
            try:
                to_add += dico_genes[gene]
            except KeyError:
                pass
        string_reaction_rule = " or ".join(to_add)
        if string_reaction_rule:
            x = copy.deepcopy(reac)
            x.gene_reaction_rule = string_reaction_rule
            new_model.add_reactions([x])
    return new_model


def pipeline(ini, blast = True, identity = 50, diff = 30, e_val = 1e-100, coverage = 20, bit_score = 300):
    """The function that launches the entire pipeline of analysis
    and selections to create a new model.
    
    ARGS:
        ini -- the initialistion file containing all the following parameters:
            WDref -- the working directory where to find the ref_gem.
            WDsub -- the working directory where to find the queryFile and subjectFile.
            ref_gem -- the reference model (sbml model compatible with COBRA).
            queryFile -- the fasta file of the model.
            subjectFile -- the fasta file of the subject.
            modelName -- string - the name for the new model.
        blast -- default value means the blast as not been done 
        and will be made, else, loads it from the working directory given.
        identity -- the treshold value of identity to select the subject genes.
        diff -- the percentage of length difference tolerated between subject and query. 
        e_val -- the minimum E-Value chosen. 
        coverage -- the minimum percentage of coverage of the match.
        bit_score -- the minimum Bit-Score chosen.
    RETURN:
        new_model -- the subject COBRA model.
    """
    #Reading of the parameter's file
    param = read_config(ini)
    WDref = param["MODEL"]["PATH"]
    ref_gem = param["MODEL"]["GEM"]
    queryFile = param["MODEL"]["FASTA"]
    WDsub = param["SUBJECT"]["PATH"]
    subjectFile = param["SUBJECT"]["FASTA"]
    modelName = param["SUBJECT"]["NAME"]
    
    model = cobra.io.read_sbml_model(WDref + ref_gem)
    if blast:
        blast_res = blast_run(WDref, WDsub, model, queryFile, subjectFile)
        save_obj(blast_res, WDsub + "resBlastp")
    else:
        blast_res = load_obj(WDsub + "resBlastp")
    dico_genes = select_genes(blast_res, identity, diff, e_val, coverage, bit_score)
    new_model = drafting(model, dico_genes, modelName)
    new_model.add_metabolites(model.metabolites)
    cobra.io.save_json_model(new_model, WDsub + modelName + ".json")
    
    ###Printing of verifications
    no_results = []
    for key in blast_res.keys():
        if not blast_res[key]:
            no_results.append(key)
    print("The",len(no_results),"genes that have no matches : ", no_results)
    ###Counting of different values
    nb_values = []
    for val in dico_genes.values():
        for i in val:
            nb_values.append(i)
    compt = 0
    for reac in model.reactions:
        if reac.gene_reaction_rule:
            compt += 1
    print("Model : %s\nStats for the reference model :\n\
- Nb of genes : %i\n- Nb of reactions : %i\n-> whose are associated to gene(s) : %i\n\
Stats for the new model :\n- Nb of genes : %i\n- Nb of reactions : %i" 
    %(modelName, len(model.genes), len(model.reactions), compt,
    len(new_model.genes), len(new_model.reactions)))
    print("----------------------------------------")
    return new_model


if __name__=='__main__':
    #Lauching the program for the 5 organism on which I'm working
    pipeline("/home/asa/INRAE/Work/Drafts/Tomato_Aracyc/TomatoAracyc.ini", blast = False)
    pipeline("/home/asa/INRAE/Work/Drafts/Kiwi_Aracyc/KiwiAracyc.ini", blast = False)
    pipeline("/home/asa/INRAE/Work/Drafts/Cucumber_Aracyc/CucumberAracyc.ini", blast = False)
    pipeline("/home/asa/INRAE/Work/Drafts/Cherry_Aracyc/CherryAracyc.ini", blast = False)
    pipeline("/home/asa/INRAE/Work/Drafts/Camelina_Aracyc/CamelinaAracyc.ini", blast = False)