#!/usr/bin/env python
#script designed to use blast.db and get accession numbers to pull down.
#This pulls down those with only one choice and pulls longest for those with multiple

def resolve_seqs(blastdb, email):
    import os, sys, sqlite3, re, time, itertools
    from Bio import Seq, Entrez, SeqIO
    from blastlib.clean_seq_funcs import resolve_seqs, alignment_reg, alignment_comp, alignment_rev_comp, identity_calc, tiling
    from cleanlib.databasing import get_seqs_from_sqldb_GI
    conn = sqlite3.connect(blastdb)
    c = conn.cursor()
    Entrez.email = email
    GI_nums_all = set()
    GI_nums_single = set()
    GI_nums_all_COI = set()
    GI_nums_single_COI = set()
    mito_COI = set()
    genes = set()
    dic = {}
    dic_COI = {}
    dic_single = {}
    dic_mult = {}
    count2 = 1
    records = []
    #this gets list of all taxa/genes regardless if they have multiple gene choices or not
    for iter in c.execute("SELECT tc_id, Gene_name, GI, hit_length FROM blast WHERE tc_id NOT NULL AND Gene_name != 'COI_trnL_COII' GROUP BY tc_id, Gene_name, GI;"):
        GI_nums_all.add(str(iter[0])+"_"+str(iter[1])+"|"+str(iter[2])+"_"+str(iter[3]))
    #this gets a list of all taxa/genes if they only have one gene choice
    for iter in c.execute("SELECT tc_id, Gene_name, GI, hit_length FROM blast WHERE tc_id NOT NULL AND Gene_name != 'COI_trnL_COII' GROUP BY tc_id, Gene_name HAVING COUNT(*) =1;"):
        GI_nums_single.add(str(iter[0])+"_"+str(iter[1])+"|"+str(iter[2])+"_"+str(iter[3]))
    #this give me all the tc_idss that have multiple gene choices
    #tc_id_gene|GI_hit_length
    GI_nums = GI_nums_all-GI_nums_single
    GI_nums_single_GIs = []
    for i in GI_nums_single:
        GI_nums_single_GIs.append(re.split('_|\|', i)[-2])
    
    GI_nums_single_str = str(GI_nums_single_GIs).replace("[", "(").replace("]", ")")
    c.execute("UPDATE blast SET Decision='Only choice/chosen' WHERE GI IN " + GI_nums_single_str + ";")
    #do the same with COI
    #this gets list of all taxa/genes regardless if they have multiple gene choices or not
    for iter in c.execute("SELECT tc_id, Gene_name, GI, hit_length FROM blast WHERE tc_id NOT NULL AND Gene_name == 'COI_trnL_COII' GROUP BY tc_id, Gene_name, GI;"):
        GI_nums_all_COI.add(str(iter[0])+"_"+str(iter[1])+"|"+str(iter[2])+"_"+str(iter[3]))
    #this gets a list of all taxa/genes if they only have one gene choice
    for iter in c.execute("SELECT tc_id, Gene_name, GI, hit_length FROM blast WHERE tc_id NOT NULL AND Gene_name = 'COI_trnL_COII' GROUP BY tc_id HAVING COUNT(*) =1;"):
        GI_nums_single_COI.add(str(iter[0])+"_"+str(iter[1])+"|"+str(iter[2])+"_"+str(iter[3]))
    #this give me all the GIs that have multiple gene choices
    GI_nums_mult_COI = GI_nums_all_COI-GI_nums_single_COI
    for i in GI_nums_single_COI:
        if int(i.split("_")[-1]) > 3000:
            GI_nums_mult_COI.add(i)
            mito_COI.add(i)
            
    for i in mito_COI:
        GI_nums_single_COI.remove(i)
    
    #makes a dictionary of lists for each multiple taxa/gene choice
#    for i in GI_nums_single:
#       if i.split("|")[0] in dic.keys():
#            dic_list = dic[i.split("|")[0]]
#            dic_list.append(i.split("|")[1])
#            dic[i.split("|")[0]] = dic_list
#        else:
#            dic[i.split("|")[0]] = [i.split("|")[1]]
#        genes.add(re.split('_|\|', i)[1])    
    for i in GI_nums:
        if i.split("|")[0] in dic.keys():
            dic_list = dic[i.split("|")[0]]
            dic_list.append(i.split("|")[1])
            dic[i.split("|")[0]] = dic_list
        else:
            dic[i.split("|")[0]] = [i.split("|")[1]]    
    #same for COI
    for i in GI_nums_mult_COI:
        if i.split("|")[0] in dic_COI.keys():
            dic_list = dic_COI[i.split("|")[0]]
            dic_list.append(i.split("|")[1])
            dic_COI[i.split("|")[0]] = dic_list
        else:
            dic_COI[i.split("|")[0]] = [i.split("|")[1]]
    for iter in c.execute("SELECT Gene_name from blast GROUP BY Gene_name;"):
        genes.add(iter[0])            
   
    countall = 0
    #deal with lengths of COI and add to dic to try and resolve
    print("Trying to resolve COI/COII sequences")
    for i in dic_COI:
        countall += 1
        #print(i)
        #print(countall)
        print(str(round(float(countall)/float(len(dic_COI))*100, 2))+'%')
        lengths = [int(m.split('_')[1]) for m in dic_COI[i]]
        individual = [dic_COI[i][x] for x, l in enumerate(lengths) if l < 2000]
        whole = [dic_COI[i][x] for x, l in enumerate(lengths) if l > 2000 and l < 3000]
        mito = [dic_COI[i][x] for x, l in enumerate(lengths) if l > 3000]
        if len(mito) > 0:
            mitoinGI = [mito[0].split("_")[0]]
            iterator = get_seqs_from_sqldb_GI(mitoinGI, "hseq", blastdb, c)
            for seq in iterator:
                records.append(seq)
            c.execute("UPDATE blast SET Decision='Mito or chloro sequence/Chosen' WHERE GI='" + mitoinGI[0] + "';")
        elif len(whole) > 0:
            #pick whole
            if len(whole) == 1:
                GI_nums_single.add(i+"|"+whole[0])
                c.execute("UPDATE blast SET Decision='Full length sequence/Chosen' WHERE GI='" + whole[0].split("_")[0] + "';")
            else:
                #to pipeline
                dic[i] = whole
        elif len(individual) > 0:
            #pick individual
            if len(individual) == 1:
                GI_nums_single.add(i+"|"+individual[0])
                c.execute("UPDATE blast SET Decision='Only choice/chosen' WHERE Name_num='" + individual[0].split("_")[0] + "';")
                
            else:
#                print(individual)
                result = []
                ranges = {}
                current_start = -1
                current_stop = -1
                whole_length = 0
                #do tiling
                for m in [x.split('_')[0] for x in individual]:
                    idens, start_stop = tiling([m], 'COI_trnL_COII', blastdb, c)
                    start, end = start_stop[0]
                    #uses gi for danaus chrysippus 
                    for iden in idens:
                        if iden > 70:
                            #make dic of lists
                            if (start, end) in ranges.keys():
                                ranges_dic_list = ranges[(start, end)]
                                ranges_dic_list.append(m)
                                ranges[(start, end)] = ranges_dic_list
                            else:
                                ranges[(start, end)] = [m]
                        else:
                            print('Alignment below 70')
                            #print(GIs_to_align)
                if len(ranges) == 0:
                    c.execute("UPDATE blast SET Decision='Sequence does not align well (<70%) to input query sequence/not chosen' WHERE Name_num='" + i + "';")
                    print('All alignments below 70, printing to file')
                    with open("COI_hand_check.txt", "a") as a:
                        a.write(i + '\n')
                #get merged range
                for start, stop in sorted(ranges.keys()):
                    if start > current_stop:
                        result.append((start, stop))
                        current_start, current_stop = start, stop
                    else:
                        current_stop = max(current_stop, stop)
                        result[-1] = (current_start, current_stop)
                for n in result:
                    whole_length += n[1] - n[0] + 1
                #go through each combination of ranges to get 95% of whole range
                for L in range(1, len(ranges)+1):
                    max_perc = 0
                    for subset in itertools.combinations(ranges.keys(), L):
                        comb_length = 0
                        #for each combination, get merged length
                        current_start = -1
                        current_stop = -1
                        result = []
                        for start, stop in sorted(subset):
                            if start > current_stop:
                                result.append((start, stop))
                                current_start, current_stop = start, stop
                            else:
                                current_stop = max(current_stop, stop)
                                result[-1] = (current_start, current_stop)
                        for x in result:
                            comb_length += x[1] - x[0] + 1
                        if whole_length >= comb_length:
                            perc = float(comb_length)/float(whole_length)
                            if perc > max_perc:
                                max_perc = perc
                                max_subset = set()
                                max_subset.add(subset)
                            elif perc == max_perc:
                                max_subset.add(subset)
                            else:
                                pass  
                        else:
                            pass
                    # goes through all combinations in a level before breaking
                    if max_perc > .95:
                        break
                final_tiling = [(0, 0)]*L
                for combination in max_subset:
                    for x, comb_frag in enumerate(sorted(combination)):
                        if comb_frag[1] - comb_frag[0] + 1 > final_tiling[x][1] - final_tiling[x][0] + 1:
                            final_tiling[x] = comb_frag
                possible_GIs = [ranges[x] for x in final_tiling]
                count = 0
                for m in possible_GIs:
                    if len(m) == 1:
                        c.execute("UPDATE blast SET Decision='Only or best choice in tiling analysis/chosen' WHERE GI='" + m[0] + "';")
                        GI_nums_single.add(i+"|"+m[0] + "_0")
                    else:
                        if count == 0:
                            dic[i] = m
                            count += 1
                        else:
                            dic[i + "_" + str(count)] = m
                            count += 1
                        # merge ranges - if same number of ranges as original, keep all,
                        # want the least number to overlap 95% of whole range
                        # try each comb from low to high and if hits 95%, choose those
                        # if multiple higher than 95%, choose one with best %
                        # if multiple with same % and same numb of combs- multiple
    #print(dic)
 #   sys.exit()
    conn.commit()
    SeqIO.write(records, "mito_COI.fa", "fasta")
    #pulls out the GIs with first, the longest number of ATCGs and second, the longest length and makes dictionary
    print("Trying to resolve all other sequences")
    count = 0
    for i in dic:
        GIlist = []
        for n in dic[i]:
            GIlist.append(n.split("_")[0])
        dic[i] = resolve_seqs(GIlist, blastdb, gene, c)
        print(str(round((float(count)/float(len(dic)))*100, 2)) + "%")
        count += 1
    #splits the ones that still have multiple (so the longest had multiple choices) and the ones that are resolved
    for i in dic:
        if len(dic[i])>1:
            dic_mult[i] = dic[i]
        else:
            dic_single[i] = dic[i]
    for i in genes:
        finalGInums_only1 = set()
        finalGInums_longest = set()
        for n in dic_single.keys():
            if i == n.split("_", 1)[1]:
                finalGInums_longest.add(''.join(dic_single[n]))
        for n in GI_nums_single:
            if i == n.split("_", 1)[1].split("|")[0]:
                finalGInums_only1.add(re.split('_|\|', n)[-2])
        for n in GI_nums_single_COI:
            c.execute("UPDATE blast SET Decision='Only choice/chosen' WHERE GI='" + re.split('_|\|', n)[-2] + "';")
            if i == n.split("_", 1)[1].split("|")[0]:
                finalGInums_only1.add(re.split('_|\|', n)[-2]) 
        with open("final_GIs.txt", "a") as o:
            for m in finalGInums_only1:
                o.write(str(m)+"\n")
        #this needs to go to blast_sp_parse.py
        if len(finalGInums_longest) != 0:
            with open(i + "_accession_nums_resolved.txt", "w") as o:
                for m in finalGInums_longest:
                    o.write(str(m)+"\n")
    #this needs to go to cluster.py          
    with open("multiple_gene_choices.txt", "w") as w:
        for i in dic_mult:
            w.write(i + "\t" + str(dic_mult[i]) + "\n")
    conn.commit()
    conn.close()

