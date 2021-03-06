"""
MEGNet-based describers
"""
from pathlib import Path
from typing import Optional, Any, Union, List

import pandas as pd
from megnet.models import GraphModel
from megnet.utils.models import MODEL_MAPPING, load_model
from megnet.utils.descriptor import MEGNetDescriptor

from maml.base import BaseDescriber
from maml.utils import get_full_stats_and_funcs


DEFAULT_MODEL = Path(__file__).parent / '../data/megnet_models/formation_energy.hdf5'


class MEGNetSite(BaseDescriber):
    """
    Use megnet pre-trained models as featurizer to get
    atomic features

    Reference:
    @article{chen2019graph,title={Graph networks as a universal machine
                learning framework for molecules and crystals},
            author={Chen, Chi and Ye, Weike and Zuo, Yunxing and
                Zheng, Chen and Ong, Shyue Ping},
            journal={Chemistry of Materials}, volume={31}, number={9},
            pages={3564--3572}, year={2019},publisher={ACS Publications}}
    """
    AVAILBLE_MODELS = list(MODEL_MAPPING.keys())

    def __init__(self, name: Optional[Union[str, GraphModel]] = None,
                 level: Optional[int] = None,
                 **kwargs):
        """

        Args:s
            name (str or GraphModel): model name keys, megnet model path or a MEGNet GraphModel,
                if no name is provided, the model will be Eform_MP_2019.
            level (int): megnet graph layer level
        """
        if isinstance(name, str) and name in self.AVAILBLE_MODELS:
            name_or_model = load_model(name)
        elif name is None:
            name_or_model = str(DEFAULT_MODEL)

        else:
            name_or_model = name

        self.describer_model = MEGNetDescriptor(name_or_model)

        if level is None:
            n_layers = sum([i.startswith('meg_net') for i in self.describer_model.valid_names]) // 3
            level = n_layers
        self.name = name
        self.level = level
        super().__init__(**kwargs)

    def transform_one(self, obj: Any):
        """
        Get megnet site features from structure object

        Args:
            obj (structure or molecule): pymatgen structure or molecules

        Returns:

        """
        features = self.describer_model.get_atom_features(obj, level=self.level)
        return pd.DataFrame(features)


class MEGNetStructure(BaseDescriber):
    """
    Use megnet pre-trained models as featurizer to get
    structural features. There are two methods to get structural descriptors from
    megnet models.

    mode:
        'site_stats': Calculate the site features, and then use maml.utils.stats to compute the feature-wise
            statistics. This requires the specification of level
        'site_readout': Use the atomic features at the readout stage
        'final': Use the concatenated atom, bond and global features

    Reference:
    @article{chen2019graph,title={Graph networks as a universal machine
                learning framework for molecules and crystals},
            author={Chen, Chi and Ye, Weike and Zuo, Yunxing and
                Zheng, Chen and Ong, Shyue Ping},
            journal={Chemistry of Materials}, volume={31}, number={9},
            pages={3564--3572}, year={2019},publisher={ACS Publications}}
    """
    AVAILBLE_MODELS = list(MODEL_MAPPING.keys())

    def __init__(self, name: Optional[Union[str, GraphModel]] = None, mode: str = 'site_stats',
                 level: Optional[int] = None, stats: Optional[List] = None,
                 **kwargs):
        """

        Args:s
            name (str or GraphModel): model name keys, megnet model path or a MEGNet GraphModel,
                if no name is provided, the model will be Eform_MP_2019.
            mode (str): choose one from ['site_stats', 'site_readout', 'final'].
                'site_stats': Calculate the site features, and then use maml.utils.stats to compute the feature-wise
                    statistics. This requires the specification of level
                'site_readout': Use the atomic features at the readout stage
                'final': Use the concatenated atom, bond and global features
            level (int): megnet graph layer level
        """
        if isinstance(name, str) and name in self.AVAILBLE_MODELS:
            name_or_model = load_model(name)
        elif name is None:
            name_or_model = str(DEFAULT_MODEL)
        else:
            name_or_model = name

        self.describer_model = MEGNetDescriptor(name_or_model)

        if level is None:
            n_layers = sum([i.startswith('meg_net') for i in self.describer_model.valid_names]) // 3
            level = n_layers

        self.name = name
        self.level = level
        self.mode = mode
        if stats is None:
            stats = ['min', 'max', 'range', 'mean', 'mean_absolute_error', 'mode']
        self.stats = stats
        full_stats, stats_func = get_full_stats_and_funcs(stats)
        self.full_stats = full_stats
        self.stats_func = stats_func
        super().__init__(**kwargs)

    def transform_one(self, obj: Any):
        """
        Transform structure/molecule objects into features
        Args:
            obj (Structure/Molecule): target object structure or molecule

        Returns: pd.DataFrame features

        """
        if self.mode == 'site_stats':
            features = self.describer_model.get_atom_features(obj, level=self.level)
            features_transpose = list(zip(*features))
            column_names = []
            final_features = []
            for i, f in enumerate(features_transpose):
                column_names.extend(['%d_%s' % (i, n) for n in self.full_stats])
                final_features.extend([func(f) for func in self.stats_func])
            return pd.DataFrame([final_features], columns=column_names)

        elif self.mode == 'site_readout':
            return pd.DataFrame(self.describer_model.get_set2set(obj, ftype='atom'))

        elif self.mode == 'final':
            return pd.DataFrame(self.describer_model.get_structure_features(obj))
