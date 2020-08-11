# coding: utf8
# python 3.8.2
# Antoine Laporte
# Université de Bordeaux - INRAE Bordeaux
# Reconstruction de réseaux métaboliques
# Mars - Aout 2020
"""This file is used for the gap filling of the previously reconstructed models."""

import cobra
import copy
import os
import re
import subprocess
import string
from pyasp.term import *
from urllib.request import urlopen
from meneco import query, utils, sbml, run_meneco

import utils as tools


###The three functions clean(), count() and stats() are to be used later on this pipeline but are not yet in used though.
def clean(path):
    """Function to get rid of the chevron character and uppercase fasta files.
    
    ARGS:
        path (str) -- the path to the fasta file.
    RETURN:
        res (str) -- the string uppercased and without the '>' char.
    """
    
    file = tools.read_file(path)
    res = ""
    for line in file:
        if ">" not in line:
            res += line.rstrip().upper()
    return res


def count(file, letters):
    """Function to count the occurence of the 'letters' given as argument.
    
    ARGS:
        file (str) -- the path to the file to count.
        letters (list of str) -- the char/str to count.
    RETURN:
        res (dic) -- a dictionary, each key is a str counted and the value 
        the number of occurence.
    """
    
    res = {}
    for letter in letters:
        res[letter] = 0
        for i in file:
            if letter == i:
                res[letter] += 1
    return res


def stats(res):
    """NOT USED.
    Function that transforms the dictionary of results from the 'count()' 
    function into percentages, print and return them.
    
    ARGS:
        res -- the dictionary from 'count()' (see count() for the structure).
    RETURN:
        str_res (str) -- a string containing the computed information line by line. 
    """
    
    total = 0
    str_res = ""
    for key in res.keys():
        total += res[key]
    for key in res.keys():
        str_res += str(key) + "\t" + str(res[key]) + "\t" + str(round(res[key] * 100 / total, 2)) + "\n"
        print("%s : %.0f = %.2f percent" %(key, res[key], res[key] * 100 / total))
    return str_res


def make_info(WD, DNA_file, RNA_file, prot_file, name):
    """Function to organize all the previous ones to write a .txt file for an organism.
    ARGS:
        WD (str) -- the working directory.
        DNA_file (str) -- the name of the fasta file of the total DNA.
        RNA_file (str) -- the name of the fasta file of only the transcripts.
        prot_file (str) -- the name of the fasta file of the proteins.
        name (str) -- the name for the output .txt file.
    """
    
    letterProt = "ACDEFGHIKLMNPQRSTVWY*"
    letterDNA = "CGTAN"
    str_res = "DNA stats :\n"
    DNA_file_clean = clean(WD + DNA_file)
    resDNA = count(DNA_file_clean, letterDNA)
    str_res += stats(resDNA)
    RNA_file_clean = clean(WD + RNA_file)
    resRNA = count(RNA_file_clean, letterDNA)
    str_res += "RNA stats :\n"
    str_res += stats(resRNA)
    prot_file_clean = clean(WD + prot_file)
    resProt = count(prot_file_clean, letterProt)
    str_res += "Prot stats :\n"
    str_res += stats(resProt)
    tools.write_file(WD, name + "_stats.txt", str_res)
    print(str_res)


def add_filled_reactions(WD, reacs, repair, draft, json = False):
    """Function to add the retrieved reactions to the model.
    
    ARGS:
        WD (str) -- the path to the working directory where there are the repair
        model and the draft.
        reacs (list of str) -- the list of reaction names.
        repair -- the repair model file (SBML format).
        draft -- the draft model file (SBML format).
        json (boolean) -- True if you want a save of the model in the JSON
        format instead of SBML (default).
    """
    
    repair_model = cobra.io.read_sbml_model(WD + repair)
    draft_model = cobra.io.read_sbml_model(WD + draft)
    old_size = len(draft_model.reactions)
    reac_to_blast = []
    for reac in reacs:
        reac = tools.cobra_compatibility(reac.rstrip())
        try:
            new_reac = copy.deepcopy(repair_model.reactions.get_by_id(reac))
            reac_to_blast.append([new_reac.id, new_reac.gene_reaction_rule])
            new_reac.gene_reaction_rule = ""
            draft_model.add_reactions([new_reac])
        except KeyError:
            print("No match for this reaction : ", reac)
    print("Number of reactions of the unrepaired model : %i\nNumber of reactions of the repaired model : %i" %(old_size, len(draft_model.reactions)))
    if json:
        cobra.io.save_json_model(draft_model, WD + "filled_" + draft.split(".")[0] + ".json")
    else:
        cobra.io.write_sbml_model(draft_model, WD + "filled_" + draft.split(".")[0] + ".sbml")
    tools.write_csv(WD, reac_to_blast, "rxns_to_blast_" + draft_model.id, "\t")
    
    
def make_plantnetwork(WD, metacycPath, reactionsPath):
    """Function to create a subnetwork of Metacyc containing only the Viridiplantae taxon.
    This function revealed itself useless as the output model is way too small,
    and the TAXONOMIC-RANGE field is not maintained anymore.
    
    ARGS:
        WD (str) -- the path to the working directory where to save the new model.
        metacycPath (str) -- the exact path and filename of the Metacyc model.
        reactionsPath (str) the exact path and filename of the reactions.dat file of the organism.  
    """
    reactionsFile = tools.read_file(reactionsPath)
    list_plant = []
    for line in reactionsFile:
        if "UNIQUE-ID" in line:
            try:
                unique_id = re.search('(?<=UNIQUE-ID - )[+-]*\w+(.*\w+)*(-*\w+)*', line).group(0).rstrip()
            except AttributeError:
                print("No match for : ", line)
        if "TAXONOMIC-RANGE" in line and "33090" in line:
            list_plant.append(unique_id)
    
    ###Necessary step for the gathering of short/long IDs
    dico_matching, dico_matching_rev = tools.corres_dico("/home/asa/INRAE/Work/Fusion/MetacycCorresIDs.tsv")
    
    ###Transformation of all IDs in short + long to get them from Metacyc
    new_plant_list = []
    for reac in list_plant:
        try:
            for long_reac in dico_matching[reac]:
                new_plant_list.append(long_reac)
            new_plant_list.append(reac)
        except KeyError:
            try:
                new_plant_list.append(dico_matching_rev[reac])
                new_plant_list.append(reac)
            except KeyError:
                print("No match for reac : ", reac)
    
    ###Fetching the plant reactions
    metacyc = cobra.io.read_sbml_model(metacycPath)
    meta_plant = cobra.Model(name="Metacyc Plant")
    for reac in new_plant_list:
        try:
            plant_reac = copy.deepcopy(metacyc.reactions.get_by_id(reac))
            meta_plant.add_reactions([plant_reac])
        except KeyError:
            try:
                plant_reac = copy.deepcopy(metacyc.reactions.get_by_id(reac))
                meta_plant.add_reactions([plant_reac])
            except KeyError:
                print("Reaction not found in Metacyc : ", reac)
    cobra.io.write_sbml_model(meta_plant, WD + "meta_plant.sbml")


def final_model(WD, model, transcript_corres, name):
    """Temporary function to transform the transcripts in gene_reaction_rule into its corresponding genes.
    It creates a new model that will be rid of all the 'false' genes."""
    
    dico_corres, dico_corres_rev = tools.corres_dico(transcript_corres) 
    transcript_model = cobra.io.load_json_model(WD + model)
    gene_model = cobra.Model(transcript_model.id)
    for reaction in transcript_model.reactions:
        genes = []
        list_transcripts = reaction.gene_reaction_rule.split(" or ")
        for transcript in list(filter(None, [trans.upper() for trans in list_transcripts])):
            try:
                genes.append(dico_corres_rev[transcript])
            except KeyError:
                try:
                    dico_corres[transcript]
                    genes.append(transcript)
                except KeyError:
                    print("No match for : ", transcript)
                    # genes.append(transcript) ##For the cherry
        new_reaction = copy.deepcopy(reaction)
        new_reaction.gene_reaction_rule = " or ".join(set(genes))
        gene_model.add_reactions([new_reaction])
    cobra.io.save_json_model(gene_model, WD + name + transcript_model.id + ".json")
            


def pipeline_gap_filling(WD, draft, seeds, targets, repair, enumeration = False, json = False):
    """The main function to make all the process.
    
    ARGS:
        WD (str) -- the path to the directory where to find all the needed files.
        draft (str) -- the filename of the model to enhance.
        seeds (str) -- the filename of the seeds.
        targets (str) -- the filename of the targets.
        repair (str) -- the filename of the repair model.
        enumeration (boolean) -- Meneco choice to list all the reactions found or not.
        json (boolean) -- Meneco choice of getting the result as a JSON (not working).
    """
    
    clean_draft = tools.clean_sbml(WD, draft)
    clean_repair = tools.clean_sbml(WD, repair)
    result = run_meneco(draftnet = WD + clean_draft,
                        seeds = WD + seeds,
                        targets = WD + targets,
                        repairnet = WD + clean_repair,
                        enumeration = enumeration,
                        json = json)
    print(result)
    ###This next function line will add every reactions without manual curation,
    ###uncommenting it is not advised, as it is unspecific.
    # add_filled_reactions(WD, result['Union of cardinality minimal completions'], repair, clean_draft)


if __name__=="__main__":
    ###First step : running the gap-filling process
    # ##Tomato
    # pipeline_gap_filling("/home/asa/INRAE/Work/Gap_filling/",
    #                      "TomatoFusion.sbml",
    #                      "seedsPlants.sbml",
    #                      "targetsTomato.sbml",
    #                      "metacyc.sbml")
    
    # ##Kiwi
    # pipeline_gap_filling("/home/asa/INRAE/Work/Gap_filling/",
    #                      "KiwiFusion.sbml",
    #                      "seedsPlants.sbml",
    #                      "targetsKiwi.sbml",
    #                      "metacyc.sbml")
    
    # ##Cucumber
    # pipeline_gap_filling("/home/asa/INRAE/Work/Gap_filling/",
    #                      "CucumberFusion.sbml",
    #                      "seedsPlants.sbml",
    #                      "targetsCucumber.sbml",
    #                      "metacyc.sbml")
    
    # ##Cherry
    # pipeline_gap_filling("/home/asa/INRAE/Work/Gap_filling/",
    #                      "CherryFusion.sbml",
    #                      "seedsPlants.sbml",
    #                      "targetsCherry.sbml",
    #                      "metacyc.sbml")
    
    # ##Camelina
    # pipeline_gap_filling("/home/asa/INRAE/Work/Gap_filling/",
    #                      "CamelinaFusion.sbml",
    #                      "seedsPlants.sbml",
    #                      "targetsTomato.sbml",
    #                      "metacyc.sbml")
    
    ###Second step : adding manually curated reactions
    # ##Tomato
    # reacs = tools.read_file("/home/asa/INRAE/Work/Gap_filling/reactions_to_add_Tomato.txt")
    # reacs = tools.trans_short_ID(reacs, "/home/asa/INRAE/Work/Fusion/MetacycCorresIDs.tsv")
    # add_filled_reactions("/home/asa/INRAE/Work/Gap_filling/",
    #                      reacs,
    #                      "clean_metacyc.sbml",
    #                      "clean_FusionGenesTomato.sbml",
    #                      True)
    
    # ##Kiwi
    # reacs = tools.read_file("/home/asa/INRAE/Work/Gap_filling/reactions_to_add_Kiwi.txt")
    # reacs = tools.trans_short_ID(reacs, "/home/asa/INRAE/Work/Fusion/MetacycCorresIDs.tsv")
    # add_filled_reactions("/home/asa/INRAE/Work/Gap_filling/",
    #                      reacs,
    #                      "clean_metacyc.sbml",
    #                      "clean_FusionGenesKiwi.sbml",
    #                      True)
    
    # ##Cucumber
    # reacs = tools.read_file("/home/asa/INRAE/Work/Gap_filling/reactions_to_add_Cucumber.txt")
    # reacs = tools.trans_short_ID(reacs, "/home/asa/INRAE/Work/Fusion/MetacycCorresIDs.tsv")
    # add_filled_reactions("/home/asa/INRAE/Work/Gap_filling/",
    #                      reacs,
    #                      "clean_metacyc.sbml",
    #                      "clean_FusionGenesCucumber.sbml",
    #                      True)
    
    # ##Cherry
    # reacs = tools.read_file("/home/asa/INRAE/Work/Gap_filling/reactions_to_add_Cherry.txt")
    # reacs = tools.trans_short_ID(reacs, "/home/asa/INRAE/Work/Fusion/MetacycCorresIDs.tsv")
    # add_filled_reactions("/home/asa/INRAE/Work/Gap_filling/",
    #                      reacs,
    #                      "clean_metacyc.sbml",
    #                      "clean_FusionGenesCherry.sbml",
    #                      True)
    
    # ##Camelina
    # reacs = tools.read_file("/home/asa/INRAE/Work/Gap_filling/reactions_to_add_Camelina.txt")
    # reacs = tools.trans_short_ID(reacs, "/home/asa/INRAE/Work/Fusion/MetacycCorresIDs.tsv")
    # add_filled_reactions("/home/asa/INRAE/Work/Gap_filling/",
    #                      reacs,
    #                      "clean_metacyc.sbml",
    #                      "clean_FusionGenesCamelina.sbml",
    #                      True)
    
    ###Third step : change the transcripts into genes (if not done before)
    # ##Tomato
    # final_model("/home/asa/INRAE/Work/", "finalTomato.json", "/home/asa/INRAE/Work/mpwt/log/transcript_corres_SolLyPHFalse.csv", "final_gene")
    
    # ##Kiwi
    # final_model("/home/asa/INRAE/Work/", "finalKiwi.json", "/home/asa/INRAE/Work/mpwt/log/transcript_corres_ActChPHFalse.csv", "final_gene")
    
    # ##Cucumber
    # final_model("/home/asa/INRAE/Work/", "finalCucumber.json", "/home/asa/INRAE/Work/mpwt/log/transcript_corres_CucSaPHFalse.csv", "final_gene")
    
    # ##Cherry
    # ##To get rid of the "new_gene" (add "genes.append(transcript)" after the last except to keep the normal genes !)
    # final_model("/home/asa/INRAE/Work/", "finalCherry.json", "/home/asa/INRAE/Work/Fusion/corres_gff_genes_cherry_upper.csv", "final_cor")
    # ##Regular treatment
    # final_model("/home/asa/INRAE/Work/", "final_corCherry.json", "/home/asa/INRAE/Work/mpwt/log/transcript_corres_PruAvPHFalse.csv", "final_gene")
    
    # ##Camelina
    # final_model("/home/asa/INRAE/Work/", "finalCamelina.json", "/home/asa/INRAE/Work/mpwt/log/transcript_corres_CamSaPHFalse.csv", "final_gene")