#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Feb 24 2018

@author: kushal

Chatzigeorgiou Group
Sars International Centre for Marine Molecular Biology

GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007
"""

import pandas as pd
import numpy as np
import pickle
import json
from copy import deepcopy
from uuid import uuid4, UUID
from typing import Tuple, List


class DataBlockNotFound(Exception):
    """ Requested data block not found """
    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(*args, **kwargs): # real signature unknown
        """ Create and return a new object.  See help(type) for accurate signature. """
        pass


class DataBlockAlreadyExists(Exception):
    """ Data block already exists in HistoryTrace """
    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(*args, **kwargs): # real signature unknown
        """ Create and return a new object.  See help(type) for accurate signature. """
        pass


class OperationNotFound(Exception):
    """ Requested operation not found in data block """
    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(*args, **kwargs): # real signature unknown
        """ Create and return a new object.  See help(type) for accurate signature. """
        pass


class HistoryTrace:
    """
    Structure of a history trace:

    A dict with keys that are the block_ids. Each dict value is a list of operation_dicts.
    Each operation_dict has a single key which is the name of the operation and the value of that key is the operation parameters.

        {block_id_1: [
                        {operation_1:
                            {
                             param_1: a,
                             param_2: b,
                             param_n, z
                             }
                         },

                        {operation_2:
                            {
                             param_1: a,
                             param_n, z
                             }
                         },
                         ...
                        {operation_n:
                            {
                             param_n: x
                             }
                         }
                     ]
         block_id_2: <list of operation dicts>,
         ...
         block_id_n: <list of operation dicts>
         }
    """
    def __init__(self, history: dict = None, data_blocks: list = None):
        if None in [history, data_blocks]:
            self.data_blocks = list()
            self._history = dict()
        else:
            self.data_blocks = data_blocks
            self.history = history

    @property
    def history(self) -> dict:
        return self._history

    @history.setter
    def history(self, h):
        self._history = h

    def create_data_block(self, dataframe: pd.DataFrame) -> Tuple[pd.DataFrame, UUID]:
        block_id = uuid4()
        self.add_data_block(block_id)
        dataframe['_BLOCK_'] = uuid4()
        return dataframe, block_id

    def add_data_block(self, data_block_id: UUID):
        if data_block_id in self.data_blocks:
            raise DataBlockAlreadyExists(str(data_block_id))
        else:
            self.data_blocks.append(data_block_id)

        self.history.update({data_block_id: []})

    def add_operation(self, data_block_id: UUID, operation: str, parameters: dict):
        assert isinstance(operation, str)
        assert isinstance(parameters, dict)
        if isinstance(data_block_id, str):
            if data_block_id != 'all':
                raise ValueError("DataBlock ID must either be a UUID or 'all'")
            else:
                _ids = self.data_blocks
        else:
            _ids = [data_block_id]
        if not all(u in self.data_blocks for u in _ids):
            raise DataBlockNotFound()
        for _id in _ids:
            self.history[_id].append({operation: parameters})

    def get_data_block_history(self, data_block_id: UUID) -> list:
        if data_block_id not in self.data_blocks:
            raise DataBlockNotFound(str(data_block_id))

        return self.history[data_block_id]

    def get_operation_params(self, data_block_id: UUID, operation: str) -> dict:
        try:
            l = self.get_data_block_history(data_block_id)
            params = next(d for ix, d in enumerate(l) if operation in d)[operation]
        except StopIteration:
            raise OperationNotFound('Data block: ' + str(data_block_id) + '\nOperation: ' + operation)

        return params

    def _export(self):
        return {'history': self.history, 'data_blocks': self.data_blocks}

    def to_json(self, path: str):
        json.dump(self._export(), open(path, 'w'))

    @classmethod
    def from_json(cls, path: str):
        j = json.load(open(path, 'r'))
        return cls(history=j['history'], data_blocks=['data_blocks'])

    def to_pickle(self, path):
        pickle.dump(self._export(), open(path, 'wb'))

    @classmethod
    def from_pickle(cls, path: str):
        p = pickle.load(open(path, 'r'))
        return cls(history=p['history'], data_blocks=p['data_blocks'])

    @classmethod
    def merge(cls, history_traces: list):
        assert all(isinstance(h, HistoryTrace) for h in history_traces)
        data_blocks = [h.data_blocks for h in history_traces]

        history = dict()
        for h in history_traces:
            d = h.history
            history.update(d)

        return cls(history=history, data_blocks=data_blocks)


class BaseTransmission:
    def __init__(self, df: pd.DataFrame, history_trace: HistoryTrace, last_output: str = None):
        """
        Base class for common Transmission functions
        :param  dataframe:      Transmission dataframe
        :param  history_trace:  HistoryTrace object, keeps track of the nodes & node parameters
                                the transmission has been processed through
        """
        self.df = df
        self.history_trace = history_trace
        self.last_output = last_output
        # self.kwargs = kwargs
        # self.kwargs_keys = list(kwargs.keys())
        #
        # for key in self.kwargs_keys:
        #     setattr(self, key, kwargs[key])

    @classmethod
    def from_pickle(cls, path):
        """
        :param path: Path to the pickle file
        :return: Transmission class object
        """
        p = pickle.load(open(path, 'rb'))
        return cls(**p)

    def _make_dict(self) -> dict:
        """
        Package attributes as a dict, useful for pickling
        """
        d = {'df':              self.df,
             'history_trace':   self.history_trace}

        return d

    def to_pickle(self, path: str):
        """
        :param path: Path of where to store pickle
        """
        pickle.dump(self._make_dict(), open(path, 'wb'), protocol=4)

    def copy(self):
        return deepcopy(self)

    @classmethod
    def empty_df(cls, transmission, addCols=[]):
        """
        :param transmission: Transmission object
        :param addCols: list of columns to add
        :return: empty DataFrame with the columns in this Transmission's dataframe along with any additional columns
        that were specified.
        """
        c = list(transmission.df.columns) + addCols
        e_df = pd.DataFrame(columns=c)
        return cls(e_df, transmission.history_trace, **transmission.kwargs)


class Transmission(BaseTransmission):
    """The regular transmission class used throughout the flowchart"""
    @classmethod
    def from_proj(cls, proj_path: str, dataframe: pd.DataFrame, sub_dataframe_name: str = 'root',
                  dataframe_filter_history: dict = None):
        """
        :param proj_path: root directory of the project
        :param dataframe: Chosen Child DataFrame from the Mesmerize Project

        """
        df = dataframe.copy()
        df[['_CURVE', 'meta', 'stim_maps']] = df.apply(lambda r: Transmission._load_files(proj_path, r), axis=1)
        df['raw_curve'] = df['_CURVE']

        h = HistoryTrace()
        df, block_id = h.create_data_block(dataframe)

        params = {'sub_dataframe_name': sub_dataframe_name, 'dataframe_filter_history': dataframe_filter_history}
        h.add_operation(data_block_id=block_id, operation='spawn_transmission', parameters=params)

        return cls(df, history_trace=h, last_output='_CURVE')

    @staticmethod
    def _load_files(proj_path: str, row: pd.Series) -> pd.Series:
        """Loads npz and pickle files of Curves & Img metadata according to the paths specified in each row of the
        chosen child DataFrame in the project"""

        path = proj_path + row['CurvePath']
        npz = np.load(path)

        pik_path = proj_path + row['ImgInfoPath']
        pik = pickle.load(open(pik_path, 'rb'))
        meta = pik['meta']
        stim_maps = pik['stim_maps']
        
        return pd.Series({'_CURVE': npz.f.curve[1], 'meta': meta, 'stim_maps': [[stim_maps]]})

    @classmethod
    def merge(cls, transmissions: list):
        dfs = [t.df for t in transmissions]
        df = pd.concat(dfs)

        h = [t.history_trace for t in transmissions]
        h = HistoryTrace.merge(h)

        return cls(df, history_trace=h)


class GroupTransmission(BaseTransmission):
    """Transmission class for setting groups to individual transmissions that can later be merged into a single
    StatsTransmission"""
    @classmethod
    def from_ca_data(cls, transmission: Transmission, groups_list: list):
        """
        :param  transmission: Raw Transmission object
        :param  groups_list: List of groups to which the raw Transmission object belongs

        :return: GroupTransmission
        """
        if not (any('Peak_Features' in d for d in transmission.src) or
                    any('AlignStims' in d for d in transmission.src)):
            raise IndexError('No Peak Features or Stimulus Alignment data to group the data.')

        t = transmission.copy()

        t.df, groups_list = GroupTransmission._append_group_bools(t.df, groups_list)

        t.src.append({'Grouped': ', '.join(groups_list)})

        return cls(t.df, t.src, groups_list=groups_list)

    @classmethod
    def from_behav_data(cls, transmission: Transmission, groups_list: list):
        raise NotImplementedError

    @staticmethod
    def _append_group_bools(df: pd.DataFrame, groups_list: list) -> (pd.DataFrame, list):
        """
        :param df:
        :param groups_list:
        :return:
        """
        new_gl = []
        for group in groups_list:
            group = '_G_' + group
            new_gl.append(group)
            df[group] = True

        return df, new_gl


class StatsTransmission(BaseTransmission):
    """Transmission class that contains a DataFrame consisting of data from many groups. Columns with names that start
    with '_G_' denote groups. Booleans indicate whether or not that row belong to that group."""
    @classmethod
    def from_group_trans(cls, transmissions: list):
        """
        :param transmissions list of GroupTransmission objects
        """
        all_groups = []
        for tran in transmissions:
            assert isinstance(tran, GroupTransmission)
            all_groups += tran.groups_list

        all_groups = list(set(all_groups))

        all_dfs = []
        all_srcs = []
        for tran in transmissions:
            tran = tran.copy()
            assert isinstance(tran, GroupTransmission)
            for group in all_groups:
                if group in tran.groups_list:
                    tran.df[group] = True
                else:
                    tran.df[group] = False
            all_srcs.append(tran.src)
            all_dfs.append(tran.df)

        all_groups = list(set(all_groups))

        df = pd.concat(all_dfs)
        assert isinstance(df, pd.DataFrame)
        df.reset_index(drop=True, inplace=True)

        return cls(df, all_srcs, all_groups=all_groups)

    @classmethod
    def merge(cls, transmissions):
        """
        :param  transmissions: Transmission objects
        :type   transmissions: GroupTransmission, StatsTransmission

        :return: StatsTransmission
        """
        groups = []
        stats = []
        all_srcs = []
        all_groups = []

        for t in transmissions:
            if isinstance(t, GroupTransmission):
                groups.append(t)

            elif isinstance(t, StatsTransmission):
                stats.append(t)
                all_srcs.append(t.src)
                all_groups.append(t.all_groups)
            else:
                e = type(t)
                raise TypeError("Cannot merge type: '" + str(e) + "'\n"
                                "You must only pass GroupTransmission or StatsTransmission objects.")

        g_merge = StatsTransmission.from_group_trans(groups)

        all_groups = list(set(all_groups + g_merge.all_groups))

        all_srcs = all_srcs + g_merge.all_srcs

        all_dfs = [g_merge] + stats

        df = pd.concat(all_dfs)
        return cls(df, all_srcs, all_groups=all_groups)


