from pathlib import Path
from snakemake.io import expand
from collections import defaultdict
import itertools


def as_list(x):
    return x if isinstance(x, list) else [x]


def join_path(*args):
    path = Path(args[0])
    for d in args[1:]:
        path = path / d
    return str(path)


class ParsedConfig:
    OUTPUT_TYPES = ['full', 'embed', 'knn']

    def __init__(self, config):

        # TODO: define and check schema of config

        self.ROOT = Path(config["ROOT"])
        self.DATA_SCENARIOS = config["DATA_SCENARIOS"]
        self.SCALING = config["SCALING"]
        self.FEATURE_SELECTION = config["FEATURE_SELECTION"]
        self.METHODS = config["METHODS"]
        self.timing = config["timing"]
        self.r_env = config["r_env"]
        self.py_env = config["py_env"]
        self.conv_env = config["conv_env"]
        try:
            self.unintegrated_m = config["unintegrated_metrics"]
        except:
            self.unintegrated_m = False

    def get_all_scalings(self):
        return self.SCALING

    def get_all_feature_selections(self):
        return list(self.FEATURE_SELECTION.keys())

    # --------------------------------------------------------------------------
    # Gets all available methods. filter for framework (R/python) if needed.
    #
    # @param framework Only methods based on the framework will be retrieved.
    # one of ["python", "R", "both"], default: both
    # --------------------------------------------------------------------------
    def get_all_methods(self, framework="both"):
        all_methods = []
        for method in self.METHODS:
            is_r = self.get_from_method(method, "R")
            if framework == "both":
                all_methods.append(method)
            elif (framework == "python") and (not is_r):
                all_methods.append(method)
            elif (framework == "R") and (is_r):
                all_methods.append(method)

        return all_methods

    def get_all_scenarios(self):
        return list(self.DATA_SCENARIOS.keys())

    def get_feature_selection(self, key):
        if key not in self.FEATURE_SELECTION:
            raise ValueError(f"{key} not a valid key for scaling")
        return self.FEATURE_SELECTION[key]

    def get_from_method(self, method, key):
        if method not in self.METHODS:
            raise ValueError(f"{method} not defined as method")
        if key not in self.METHODS[method]:
            return False
            # raise ValueError(f"{key} not a valid attribute of scenario {scenario}")
        return self.METHODS[method][key]

    def get_hvg(self, wildcards, adata_path):
        n_hvgs = self.get_feature_selection(wildcards.hvg)
        if n_hvgs == 0:
            return ""
        if self.get_from_method(wildcards.method, "R"):
            path_parts = adata_path.split('.')
            path_parts[-2] += '_hvg'
            hvg_path = '.'.join(path_parts)
            return f'-v "{hvg_path}"'
        return f"-v {n_hvgs}"

    def get_from_scenario(self, scenario, key):
        if scenario not in self.DATA_SCENARIOS:
            raise ValueError(f"{scenario} not defined as scenario")
        if key not in self.DATA_SCENARIOS[scenario]:
            return False
        return self.DATA_SCENARIOS[scenario][key]

    def get_all_python_methods(self):
        return [
            method for method in self.METHODS
            if not self.get_from_method(method, "R")
        ]

    def get_all_R_methods(self):
        return [
            method for method in self.METHODS
            if self.get_from_method(method, "R")
        ]

    def get_all_wildcards(self, type_='default', methods=None, output_types=False):
        """
        TODO: include method subsetting
        Collect all wildcards for wildcard-dependent rule
        :param type_: if 'unintegrated', will treat differently than default
        :param output_types: output type or list of output types to be considered.
            If output_types==None, all output types are included.
            Useful if a certain metric is examined on a specific output type.
            Output types are ['full', 'embed', 'knn']
        :return: (comb_func, wildcards)
            comb_func: function for combining wildcards in snakemake.io.expand function
            wildcards: dictionary containing wildcards
        """
        wildcards = defaultdict(list)

        if methods is None:
            methods = self.METHODS

        if output_types is True:
            output_types = ParsedConfig.OUTPUT_TYPES
        elif isinstance(output_types, list):
            for ot_per_method in output_types:
                if ot_per_method not in ParsedConfig.OUTPUT_TYPES:
                    raise ValueError(f"{output_types} not a valid output type")

        if type_ == 'unintegrated':
            wildcards["scenario"] = self.get_all_scenarios()
            wildcards["hvg"] = ["full_feature"]
            wildcards["scaling"] = ["unscaled"]
            wildcards["method"] = ["unintegrated"]
            wildcards["o_type"] = ["full"]
            comb_func = itertools.product
        else:
            comb_func = zip
            for method in methods:
                scaling = self.SCALING.copy()
                if self.get_from_method(method, "no_scale"):
                    scaling.remove("scale")

                def reshape_wildcards(*lists):
                    cart_prod = itertools.product(*lists)
                    return tuple(zip(*cart_prod))

                if isinstance(output_types, list):
                    # output type wildcard included
                    ot_per_method = set(output_types).intersection(self.get_from_method(method, "output_type"))
                    # [x for x in output_type if x in output_types]
                    ot_per_method, method, scaling, scenarios, features = reshape_wildcards(
                        ot_per_method,
                        [method],
                        scaling,
                        self.get_all_scenarios(),
                        self.get_all_feature_selections()
                    )
                    wildcards["o_type"].extend(ot_per_method)
                    wildcards["method"].extend(method)
                    wildcards["scaling"].extend(scaling)
                    wildcards["scenario"].extend(scenarios)
                    wildcards["hvg"].extend(features)
                else:
                    method, scaling, scenarios, features = reshape_wildcards(
                        [method],
                        scaling,
                        self.get_all_scenarios(),
                        self.get_all_feature_selections()
                    )
                    wildcards["method"].extend(method)
                    wildcards["scaling"].extend(scaling)
                    wildcards["scenario"].extend(scenarios)
                    wildcards["hvg"].extend(features)

        return comb_func, wildcards

    def get_integrated_for_metrics(self, rules, method):
        if method == "unintegrated":
            return Path(rules.integration_prepare.output).with_suffix(".h5ad")
        elif self.get_from_method(method, "R"):
            return rules.convert_RDS_h5ad.output
        else:
            return rules.integration_run_python.output

    def get_celltype_option_for_integration(self, wildcards):
        if self.get_from_method(wildcards.method, "use_celltype"):
            label_key = self.get_from_scenario(wildcards.scenario, key="label_key")
            return f"-c {label_key}"
        return ""