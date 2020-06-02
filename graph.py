# coding: utf8
# python 3.8.2
# Antoine Laporte
# Université de Bordeaux - INRAE Bordeaux
# Reconstruction de réseaux métaboliques
# Mars - Aout 2020
"""This file is used as a tool to gather data to make graph, 
do some calculations on my newly made drafts and so on..."""

import matplotlib.pyplot as plt
from statistics import mean
import csv
from upsetplot import plot
from upsetplot import from_memberships
import copy
import cobra
from supervenn import supervenn
import re

import blasting


def write_file(WD, list_value, name):
    """Function to save a file as a CSV format."""
    with open(WD + name + '.csv', 'w', newline = '') as file:
        writer = csv.writer(file)
        for f in list_value:
            writer.writerow(f)


def read_file(WD, file):
    """Function to load a file written under the previous model of save."""
    res = []
    f = open(WD + file, "r")
    for line in f.readlines():
        res.append(line.rstrip())
    return res


def graph_identity(data):
    """Function to gather the identity value of the blastp results
    (obtained with blasting.py) and prepare them for a plot.
    
    ARGS:
        data -- the dictionary containing the genes and the blastp result for each.
    RETURN:
        x -- list of x-axis values depending on the treshold value.
        y -- list of y-axis values depending on the treshold value.
    """
    
    res_plot = {}
    treshold = 5
    while treshold <= 100:
        count = 0
        for key in data.keys():
            for res in data[key]:
                if float(res.split(",")[6]) >= treshold:
                    count+=1
        res_plot[treshold] = count
        treshold+=5
    x, y = list(res_plot.keys()), list(res_plot.values())
    return x, y


def get_score(data):
    """Function that gathers the Score of all the blastp
    results and returns a list of these values."""
    
    list_value = []
    for key in data.keys():
        for res in data[key]:
            list_value.append(float(res.split(",")[7]))
    return list_value


def get_e_value(data):
    """Function that gathers the E-Value of all the blastp
    results and returns a list of these values."""
    
    list_value = []
    for key in data.keys():
        for res in data[key]:
            list_value.append(float(res.split(",")[8]))
    return list_value


def get_bit_score(data):
    """Function that gathers the Bit-Score of all the blastp
    results and returns a list of these values."""
    
    list_value = []
    for key in data.keys():
        for res in data[key]:
            list_value.append(float(res.split(",")[9]))
    return list_value


def get_all_scores(organism, data):
    """Function that gathers all the previous scores of all the blastp
    results and returns a list of these values, with the organism name as first value.
    This function is used to make graph with the R script 'regressions.R'"""
    
    list_value = []
    for key in data.keys():
        for res in data[key]:
            spl = res.split(",")
            list_value.append([
                organism,
                spl[2],
                float(spl[6]),
                float(spl[7]),
                float(spl[8]),
                float(spl[9])])
    return list_value


def make_upsetplot(WD, data, name):
    """Function to make an UpSetPlot.
    
    ARGS:
        WD -- the working directory to save the result.
        data -- the dictionary containing the organisms as keys
        and the genes/reactions/others to treat for the UpSetPlot.
    """
    
    clusters = get_clusters(list(data.keys()))
    [clusters.insert(0,[key]) for key in data.keys()]
    count = []
    for c in clusters:
        others = list(data.keys())
        listInter = []
        for x in c:
            others.remove(x)
            listInter.append(set(data[x]))
        count.append(similiraty_count(data, listInter, others))
    my_upsetplot = from_memberships(clusters, count)
    plot(my_upsetplot, show_counts = '%d', totals_plot_elements = 3)
    plt.suptitle("Unique intersection for each possible cluster")
    plt.savefig(WD + name + ".pdf")
    plt.show()


def similiraty_count(data, args, others):
    """Function which is part of the process to make the UpSetPlot,
    counting and retourning the similarities between the clusters."""
    
    cluster_set = set.intersection(*args)
    for i in others:
        cluster_set = cluster_set.difference(set(data[i]))
    return len(cluster_set)


def get_clusters(liste):
    """Function to create every individual cluster depending on 
    the number of organisms given to the UpSetPlot function."""
    
    res = []
    final_res = []
    for i in range(len(liste)-1):
        if i == 0:
            for x in liste:
                z = liste.index(x)
                for i in range(len(liste) - z - 1):
                    res.append([x, liste[z + i + 1]])
            [final_res.append(i) for i in res]
        else:
            res = get_sub_clusters(liste, res)
            [final_res.append(i) for i in res]
    return final_res


def get_sub_clusters(liste, res):
    """Subfunction of the clusters (algorithmic architecture)."""
    
    sub_res = []
    for y in res:
        z = liste.index(y[len(y)-1])
        for i in range(z + 1, len(liste)):
            x = copy.deepcopy(y)
            x.append(liste[i])
            sub_res.append(x)
    return sub_res


def data_venn(WD, model, name):
    """Function to gather the reactions in a model and write them into a CSV file.
    Used to make VENN graph"""
    
    list_id = []
    for reac in model.reactions:
        list_id.append([reac.id])
    write_file(WD, list_id, name + "_id_reac")


def help_treshold(WD, ini):
    """Function to help choosing the treshold value,
    personal use only, to combine with the R script 'tresholdSearch.R'"""
    
    listValues = []
    for i in range(101):
        test = 10 * i
        ###Putting the test values instead of default values
        draft = blasting.pipeline(ini, 0, 100, 1, 0, test)
        listValues.append([test, len(draft.genes), len(draft.reactions)])
    listValues.insert(0,["Bit_Score", "Nb genes", "Nb reactions"])
    write_file(WD, listValues, "Treshold")


if __name__=="__main__":
    ###Files and working directory###
    WD = '/home/asa/INRAE/Work/Drafts/'
    #AraGem models
    WDtom = '/home/asa/INRAE/Work/Drafts/Tomato_Arabidopsis/'
    WDkiw = '/home/asa/INRAE/Work/Drafts/Kiwi_Arabidopsis/'
    WDcuc = '/home/asa/INRAE/Work/Drafts/Cucumber_Arabidopsis/'
    WDche = '/home/asa/INRAE/Work/Drafts/Cherry_Arabidopsis/'
    WDcam = '/home/asa/INRAE/Work/Drafts/Camelina_Arabidopsis/'
    #AraCyc models
    WDtomCyc = '/home/asa/INRAE/Work/Drafts/Tomato_Aracyc/'
    WDkiwCyc = '/home/asa/INRAE/Work/Drafts/Kiwi_Aracyc/'
    WDcucCyc = '/home/asa/INRAE/Work/Drafts/Cucumber_Aracyc/'
    WDcheCyc = '/home/asa/INRAE/Work/Drafts/Cherry_Aracyc/'
    WDcamCyc = '/home/asa/INRAE/Work/Drafts/Camelina_Aracyc/'
    
    ###The new models (AraGem)
    # tomatoDraft = cobra.io.read_sbml_model(WDtom + "Tomato.xml")
    # kiwiDraft = cobra.io.read_sbml_model(WDkiw + "Kiwi.xml")
    # cucumberDraft = cobra.io.read_sbml_model(WDcuc + "Cucumber.xml")
    # cherryDraft = cobra.io.read_sbml_model(WDche + "Cherry.xml")
    # camelinaDraft = cobra.io.read_sbml_model(WDcam + "Camelina.xml")
    
    ###The new models (AraCyc)
    # tomatoDraftCyc = cobra.io.load_json_model(WDtomCyc + "Tomato.json")
    # kiwiDraftCyc = cobra.io.load_json_model(WDkiwCyc + "Kiwi.json")
    # cucumberDraftCyc = cobra.io.load_json_model(WDcucCyc + "Cucumber.json")
    # cherryDraftCyc = cobra.io.load_json_model(WDcheCyc + "Cherry.json")
    # camelinaDraftCyc = cobra.io.load_json_model(WDcamCyc + "Camelina.json")

    ###Making plots###
    #Loading the data
    # tom = blasting.load_obj(WDtom + "resBlastp")
    # kiw = blasting.load_obj(WDkiw + "resBlastp")
    # cuc = blasting.load_obj(WDcuc + "resBlastp")
    # che = blasting.load_obj(WDche + "resBlastp")
    # cam = blasting.load_obj(WDcam + "resBlastp")
    
    ###Using UpSetplot
    ##AraGem
    # tomatoGenes = read_file(WDtom, "Tomato_id_reac.csv")
    # kiwiGenes = read_file(WDkiw, "Kiwi_id_reac.csv")
    # cucumberGenes = read_file(WDcuc, "Cucumber_id_reac.csv")
    # cherryGenes = read_file(WDche, "Cherry_id_reac.csv")
    # camelinaGenes = read_file(WDcam, "Camelina_id_reac.csv")
    ##AraCyc
    tomatoGenesCyc = read_file(WDtomCyc, "TomatoCyc_id_reac.csv")
    # kiwiGenesCyc = read_file(WDkiwCyc, "KiwiCyc_id_reac.csv")
    # cucumberGenesCyc = read_file(WDcucCyc, "CucumberCyc_id_reac.csv")
    # cherryGenesCyc = read_file(WDcheCyc, "CherryCyc_id_reac.csv")
    # camelinaGenesCyc = read_file(WDcamCyc, "CamelinaCyc_id_reac.csv")
    
    #Getting the AraCyc reconstruction's reactions VS Pathway Tools:
    print("Nombre réaction Aracyc perso : ", len(tomatoGenesCyc))
    
    listeReacPTtomato = []
    PTtomatoReac = open("/home/asa/INRAE/Logiciels/ptools-local/pgdbs/user/tomato2cyc/1.0/data/reactions.dat","r")
    for line in PTtomatoReac:
        if "UNIQUE-ID" in line:
            try:
                listeReacPTtomato.append(re.search('(?<=UNIQUE-ID - )\w+(.\w+)*(-\w+)*', line).group(0))
            except AttributeError:
                pass
    print("Nombre réactions PT : ", len(listeReacPTtomato))
    print("Nombre réactions en commun : ", len(set.intersection(set(listeReacPTtomato), set(tomatoGenesCyc))))
    #Supervenn Aracyc VS Pathway Tools Tomato
    # sets_list = [set(tomatoGenesCyc), set(listeReacPTtomato)]
    # species_names = ["Tomato AraCyc", "Tomato Pathway Tools"]
    # plt.show(supervenn(sets_list, species_names, figsize=(20, 10), rotate_col_annotations=True,
    #       col_annotations_area_height=1.2, sets_ordering='minimize gaps',
    #       min_width_for_annotation=10))
    
    ###Creating the dictionary to fit the function
    # dicoUpset = {"Tomato" : tomatoGenes,
    #              "Kiwi" : kiwiGenes,
    #              "Cucumber" : cucumberGenes,
    #              "Cherry" : cherryGenes,
    #              "Camelina" : camelinaGenes}
    # make_upsetplot(WD, dicoUpset, "upsetPlotAraGem")

    # dicoUpset = {"Tomato" : tomatoGenesCyc,
    #              "Kiwi" : kiwiGenesCyc,
    #              "Cucumber" : cucumberGenesCyc,
    #              "Cherry" : cherryGenesCyc,
    #              "Camelina" : camelinaGenesCyc}
    # make_upsetplot(WD, dicoUpset, "upsetPlotAraCyc")
    
    #Tried the supervenn plot, not convinced for this use
    # sets_list = [set(tomatoGenesCyc), set(kiwiGenesCyc), set(cucumberGenesCyc), set(cherryGenesCyc), set(camelinaGenesCyc)]
    # species_names = ["Tomato", "Kiwi", "Cucumber", "Cherry", "Camelina"]
    # plt.show(supervenn(sets_list, species_names, figsize=(20, 10), rotate_col_annotations=True,
    #       col_annotations_area_height=1.2, sets_ordering='minimize gaps',
    #       min_width_for_annotation=10))

    ###Get the reactions id for the Venn diagramm###
    ##First models (AraGem)
    # data_venn(WDtom, tomatoDraft, "Tomato")
    # data_venn(WDkiw, kiwiDraft, "Kiwi")
    # data_venn(WDcuc, cucumberDraft, "Cucumber")
    # data_venn(WDche, cherryDraft, "Cherry")
    # data_venn(WDcam, camelinaDraft, "Camelina")
    ##Second models (AraCyc)
    # data_venn(WDtomCyc, tomatoDraftCyc, "TomatoCyc")
    # data_venn(WDkiwCyc, kiwiDraftCyc, "KiwiCyc")
    # data_venn(WDcucCyc, cucumberDraftCyc, "CucumberCyc")
    # data_venn(WDcheCyc, cherryDraftCyc, "CherryCyc")
    # data_venn(WDcamCyc, camelinaDraftCyc, "CamelinaCyc")

    ###Help to choose the treshold###
    # help_treshold(WDtom, TomatoAracyc.ini)
    # help_treshold(WDkiw, KiwiAracyc.ini)
    # help_treshold(WDcuc, CucumberAracyc.ini)
    # help_treshold(WDche, CherryAracyc.ini)
    # help_treshold(WDcam, CamelinaAracyc.ini)

    #------Identity------#
    # tomato = graph_identity(tom)
    # kiwi = graph_identity(kiw)
    # cucumber = graph_identity(cuc)
    # cherry = graph_identity(che)
    # plt.plot(tomato[0], tomato[1], 'r', label = 'Tomato')
    # plt.plot(kiwi[0], kiwi[1], 'g', label = 'Kiwi')
    # plt.plot(cucumber[0], cucumber[1], 'b', label = 'Cucumber')
    # plt.plot(cherry[0], cherry[1], 'y', label = 'Cherry' )
    # plt.ylabel('Number of mappings')
    # plt.xlabel('Percentage of identity')
    # plt.legend(fancybox=True, framealpha=1, shadow=True, borderpad=1)
    # plt.savefig(WD + '4plots.png', dpi=300)
    # plt.show()
    
    #------E-Value------#
    # tomato_e_value = get_e_value(tom)
    # tomato_e_value.insert(0, "Tomato")
    # kiwi_e_value = get_e_value(kiw)
    # kiwi_e_value.insert(0, "Kiwi")
    # cucumber_e_value = get_e_value(cuc)
    # cucumber_e_value.insert(0, "Cucumber")
    # cherry_e_value = get_e_value(che)
    # cherry_e_value.insert(0, "Cherry")
    # total_list = [tomato_e_value, kiwi_e_value, cucumber_e_value, cherry_e_value]
    # write_csv(WD, total_list)
    
    #------Score------#
    # tomato = get_score(tom)
    # print("Mean : %f, max : %f, min : %f" % (mean(tomato), max(tomato), min(tomato)))
    
    #------Bit-Score------#
    # tomato = get_bit_score(tom)
    # print("Mean : %f, max : %f, min : %f" % (mean(tomato), max(tomato), min(tomato)))
    
    #------All Scores------#
    # tomato = get_all_scores("Tomato", tom)
    # tomato.insert(0,["Organism", "Gene", "Identity", "Score", "E_Value", "Bit_Score"])
    # write_csv(WDtom, tomato, "tomato_values")
    
    # kiwi = get_all_scores("Kiwi", kiw)
    # kiwi.insert(0,["Organism", "Gene", "Identity", "Score", "E_Value", "Bit_Score"])
    # write_csv(WDkiw, kiwi, "kiwi_values")
    
    # cucumber = get_all_scores("Cucumber", cuc)
    # cucumber.insert(0,["Organism", "Gene", "Identity", "Score", "E_Value", "Bit_Score"])
    # write_csv(WDcuc, cucumber, "cucumber_values")
    
    # cherry = get_all_scores("Cherry", che)
    # cherry.insert(0,["Organism", "Gene", "Identity", "Score", "E_Value", "Bit_Score"])
    # write_csv(WDche, cherry, "cherry_values")
    
    # camelina = get_all_scores("Camelina", cam)
    # camelina.insert(0,["Organism", "Gene", "Identity", "Score", "E_Value", "Bit_Score"])
    # write_csv(WDcam, camelina, "camelina_values")
    
    #---Calculs savants---#    
    # x = 10
    # mean_score = 0
    # mean_e_value = 0
    # mean_bit_score = 0
    # score = 0
    # e_value = 0
    # bit_score = 0
    # count = 0
    # for i in total:
    #     mean_score += i[2]
    #     mean_e_value += i[3]
    #     mean_bit_score += i[4]
    #     if i[1] > x:
    #         score += i[2]
    #         e_value += i[3]
    #         bit_score += i[4]
    #         count += 1
    # mean_score /= len(total)
    # mean_e_value /= len(total)
    # mean_bit_score /= len(total)
    # print("- Means with identity > %i :\nScore : %f\nE-Value : %f\nBit-Score : %f" % (x, score/count, e_value/count, bit_score/count))
    # print("\n- Total means :\nScore : %f\nE-Value : %f\nBit-Score : %f" % (mean_score, mean_e_value, mean_bit_score))