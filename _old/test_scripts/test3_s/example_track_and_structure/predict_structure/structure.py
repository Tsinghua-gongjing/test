#-*- coding:utf-8 -*-

import os, sys, commands, random, time


"""

predictStructure(Seq, Shape=[], bp_constraint=[], paris_block="", mfe=True, clean=True)

"""



def build_SHAPE_constraint(shape_list, file_name):
    SHAPE = open(file_name, 'w')
    for idx in range(len(shape_list)):
        if shape_list[idx] != "NULL":
            print >>SHAPE, "%d\t%s" % (idx+1, shape_list[idx])
        else:
            print >>SHAPE, "%d\t%s" % (idx+1, -999)
    SHAPE.close()

def build_Single_Seq_Fasta(sequence, file_name):
    SEQ = open(file_name, 'w')
    print >>SEQ, ">test\n%s" % (sequence, )
    SEQ.close()

def build_bp_constraint(bp_constraint, file_name):
    """ 
    bp_constraint: [[1,10], [2,9], [3,8]...] 1-based
    """
    OUT = open(file_name, 'w')
    print >>OUT, "DS:\n-1\nSS:\n-1\nMod:\n-1"
    print >>OUT, "Pairs:"
    for left, right in bp_constraint:
        print >>OUT, "%s %s" % (left, right)
    print >>OUT, "-1 -1"
    print >>OUT, "FMN:\n-1\nForbids:\n-1 -1\n"
    OUT.close()


def predictStructure(Seq, Shape=[], bp_constraint=[], mfe=True, clean=True, si=-0.6, sm=1.8, md=0):
    """Predict RNA Structure using RNAfold
    Seq: sequence
    Shape: shape
    bp_constraint: [[1,10], [2,9], [3,8]...] 1-based
    The length of each seq must be equal to shape
    """
    randID = random.randint(10000,99999)
    
    tmp_fa_file = "/tmp/tmp_%s.fa" % (randID, )
    tmp_shape_file = "/tmp/tmp_%s.shape" % (randID, )
    tmp_ct_file = "/tmp/tmp_%s.ct" % (randID, )
    tmp_constrain_file = "/tmp/tmp_%s.const" % (randID, )
    
    Fold_CMD = "Fold-smp %s %s -si %s -sm %s"
    param_list = [tmp_fa_file, tmp_ct_file, si, sm]
    # prepare tmp.fa
    build_Single_Seq_Fasta(Seq, tmp_fa_file)
    
    if Shape:
        assert( len(Seq) == len(Shape) )
        build_SHAPE_constraint(Shape, tmp_shape_file)
        Fold_CMD += " --SHAPE %s"
        param_list.append(tmp_shape_file)
    
    if bp_constraint:
        assert(isinstance(bp_constraint, list))
        build_bp_constraint(bp_constraint, tmp_constrain_file)
        Fold_CMD += " --constraint %s"
        param_list.append(tmp_constrain_file)
    if mfe:
        Fold_CMD += " -mfe"
    if md != 0:
        Fold_CMD += " --maxdistance %s"
        param_list.append(md)
    CMD = Fold_CMD % tuple(param_list)
    CMD += ' > /dev/null'
    print CMD
    os.system(CMD)
    
    ct2dot_cmd = "ct2dot %s %d /dev/stdout"
    if not mfe:
        return_code, return_string = commands.getstatusoutput( "grep \"ENERGY\" %s | wc -l" % (tmp_ct_file, ) )
        structure_number = int( return_string.strip() )
        structure_list = []
        regex_cap_free_energy = re.compile("=\s*(\-+[\d\.]+)")
        for idx in range(structure_number):
            return_code, return_string = commands.getstatusoutput( ct2dot_cmd % (tmp_ct_file, idx+1) )
            energy = float(regex_cap_free_energy.findall(return_string.split('\n')[0])[0])
            structure = return_string.split('\n')[2]
            structure_list.append( (energy, structure) )
    else:
        return_code, return_string = commands.getstatusoutput( ct2dot_cmd % (tmp_ct_file, 1) )
        structure = return_string.split('\n')[2]
        structure_list = structure
    
    # clean
    if clean:
        os.remove(tmp_fa_file); os.remove(tmp_ct_file);
        if os.path.isfile(tmp_constrain_file):
            os.remove(tmp_constrain_file)
        if os.path.isfile(tmp_shape_file):
            os.remove(tmp_shape_file)
    return structure_list


def bi_fold(seq_1, seq_2, local_pairing=False, mfe=True):
    import random
    randID = random.randint(10000,999999)
    seq_1_fn = "/tmp/seq_%s_1.fa" % (randID, )
    seq_2_fn = "/tmp/seq_%s_2.fa" % (randID, )
    ct_fn = "/tmp/ss_%s.ct" % (randID, )
    
    build_Single_Seq_Fasta(seq_1, seq_1_fn)
    build_Single_Seq_Fasta(seq_2, seq_2_fn)
    if not local_pairing:
        CMD = "bifold-smp --intramolecular %s %s %s > /dev/null" % (seq_1_fn, seq_2_fn, ct_fn)
    else:
        CMD = "bifold-smp %s %s %s > /dev/null" % (seq_1_fn, seq_2_fn, ct_fn)
    
    print CMD
    os.system(CMD)
    return_code, return_string = commands.getstatusoutput( "grep ENERGY %s | wc -l" % (ct_fn, ) )
    structure_number = int( return_string.strip() )
    structure_list = []
    ct2dot_cmd = "ct2dot %s %d /dev/stdout"
    for idx in range(structure_number):
        if mfe and idx == 1:
            break
        return_code, return_string = commands.getstatusoutput( ct2dot_cmd % (ct_fn, idx+1) )
        lines = return_string.split('\n')
        energy = float(lines[0].strip().split()[-2])
        structure = return_string.split()[8]
        structure_list.append( (energy, lines[2]) )
    cur_seq = seq_1 + "III" + seq_2
    os.system("rm %s %s %s" % (seq_1_fn, seq_2_fn, ct_fn))
    if mfe:
        return structure_list[0][1]
    else:
        return cur_seq, structure_list


def unique_list(inList):
    uniq_list = []
    duplicate_idx_list = []
    for idx, item in enumerate(inList):
        if item not in uniq_list:
            uniq_list.append(item)            
    return uniq_list


def search_TT_cross_linking(sequence, ct_list):
    cross_link_points = []
    
    for ct in ct_list:
        assert(ct[0]<ct[1]<=len(sequence))
        
        top_left_base = top_center_base = top_right_base = '.'
        bot_left_base = bot_center_base = bot_right_base = '.'
        
        if ct[1] != len(sequence):
            top_left_base = sequence[ct[1]]
        top_center_base = sequence[ct[1]-1]
        top_right_base = sequence[ct[1]-2]
        
        if ct[0] != 1:
            bot_left_base = sequence[ct[0]-2]
        bot_center_base = sequence[ct[0]-1]
        bot_right_base = sequence[ct[0]]
        
        top_U = True if (top_center_base == 'T' or top_center_base == 'U') else False
        bot_U = True if (bot_center_base == 'T' or bot_center_base == 'U') else False
        
        top_left_flanking_U = True if (top_left_base == 'T' or top_left_base == 'U') else False
        top_right_flanking_U = True if (top_right_base == 'T' or top_right_base == 'U') else False
        
        bot_left_flanking_U = True if (bot_left_base == 'T' or bot_left_base == 'U') else False
        bot_right_flanking_U = True if (bot_right_base == 'T' or bot_right_base == 'U') else False
        
        if top_U and bot_left_flanking_U:
            cross_link_points.append( (ct[0]-1, ct[1]) )
        
        if top_U and bot_right_flanking_U:
            cross_link_points.append( (ct[0]+1, ct[1]) )
        
        if bot_U and top_left_flanking_U:
            cross_link_points.append( (ct[0], ct[1]+1) )
        
        if bot_U and top_right_flanking_U:
            cross_link_points.append( (ct[0], ct[1]-1) )
    
    cross_link_points.sort(key=lambda x: x[0])
    return unique_list(cross_link_points)



def dot2ct(dot):
    stack = []
    ct_list = []
    for idx, symbol in enumerate(list(dot)):
        if symbol in ('(', '<', '{', '['):
            stack.append( idx+1 )
        elif symbol in (')', '>', '}', ']'):
            ct_list.append( (stack[-1], idx+1) )
            stack.pop()
    if len(stack) != 0:
        raise Exception("Invalid structure: "+dot)
    ct_list.sort()
    return ct_list










