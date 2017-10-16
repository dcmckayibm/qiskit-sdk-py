# -*- coding: utf-8 -*-

# Copyright 2017 IBM RESEARCH. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =============================================================================
"""Utilities for File Input/Output."""


import os
import datetime
import json
from qiskit._qiskiterror import QISKitError
import qiskit
import numpy

def convert_qobj_to_json(in_item):
    """Combs recursively through a list/dictionary and finds any non-json compatible
    elements and converts them. E.g. complex ndarray's are converted to lists of strings.
    Assume that all such elements are stored in dictionaries!

    Arg:
        in_item: the input dict/list
    """

    key_list = []
    for (item_index, item_iter) in enumerate(in_item):
        if isinstance(in_item, list):
            curkey = item_index
        else:
            curkey = item_iter

        if isinstance(in_item[curkey], (list, dict)):
            #go recursively through nested list/dictionaries
            convert_qobj_to_json(in_item[curkey])
        elif isinstance(in_item[curkey], numpy.ndarray):
            #ndarray's are not json compatible. Save the key.
            key_list.append(curkey)

    #convert ndarray's to lists
    #split complex arrays into two lists because complex values are not json compatible
    for curkey in key_list:
        if in_item[curkey].dtype == 'complex':
            in_item[curkey+'_ndarray_imag'] = numpy.imag(in_item[curkey]).tolist()
        in_item[curkey+'_ndarray_real'] = numpy.real(in_item[curkey]).tolist()
        in_item.pop(curkey)

def convert_json_to_qobj(in_item):
    """Combs recursively through a list/dictionary that was loaded from json
    and finds any lists that were converted from ndarray and converts them back

    Arg:
        in_item: the input dict/list
    """

    key_list = []
    for (item_index, item_iter) in enumerate(in_item):
        if isinstance(in_item, list):
            curkey = item_index
        else:
            curkey = item_iter

            if '_ndarray_real' in curkey:
                key_list.append(curkey)
                continue

        if isinstance(in_item[curkey], (list, dict)):
            convert_json_to_qobj(in_item[curkey])

    for curkey in key_list:
        curkey_root = curkey[0:-13]
        in_item[curkey_root] = numpy.array(in_item[curkey])
        in_item.pop(curkey)
        if curkey_root+'_ndarray_imag' in in_item:
            in_item[curkey_root] = in_item[curkey_root] + 1j*numpy.array(in_item[curkey_root+'_ndarray_imag'])
            in_item.pop(curkey_root+'_ndarray_imag')

def file_datestr(folder, fileroot):
    """Constructs a filename using the current date-time

    Args:
        folder: path to the save folder
        fileroot: root string for the file

    Returns:
        String: full file path of the form 'folder/YYYY_MM_DD_HH_MM_fileroot.json'
    """

    #if the fileroot has .json appended strip it off
    if len(fileroot) > 4 and fileroot[-5:].lower() == '.json':
        fileroot = fileroot[0:-5]

    return os.path.join(folder, '{:%Y_%m_%d_%H_%M_}'.format(datetime.datetime.now())+fileroot+'.json')

def load_result_from_file(filename):
    """Load a results dictionary file (.json) to a Result object.
    Note: The json file may not load properly if it was saved with a previous
    version of the SDK.

    Args:
        filename: filename of the dictionary

    Returns:
        Result: The new Results object
        Dict: if the metadata exists it will get returned
    """

    if not os.path.exists(filename):
        raise QISKitError('File %s does not exist'%filename)

    with open(filename, 'r') as load_file:
        master_dict = json.load(load_file)

    try:
        qobj = master_dict['qobj']
        qresult_dict = master_dict['result']
        convert_json_to_qobj(qresult_dict)
        metadata = master_dict['metadata']
    except KeyError:
        raise QISKitError('File %s does not have the proper dictionary structure')

    qresult = qiskit.Result(qresult_dict, qobj)

    return qresult, metadata
