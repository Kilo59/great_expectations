import configparser
import copy
import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Mapping, Optional, Union

from great_expectations.data_context.types.base import (
    DataContextConfig,
    anonymizedUsageStatisticsSchema,
)

logger = logging.getLogger(__name__)


class AbstractDataContext(ABC):
    """
    Base class for all DataContexts that contain all context-agnostic data context operations.

    The class encapsulates most store / core components and convenience methods used to access them, meaning the
    majority of DataContext functionality lives here.
    """

    FALSEY_STRINGS = ["FALSE", "false", "False", "f", "F", "0"]
    GLOBAL_CONFIG_PATHS = [
        os.path.expanduser("~/.great_expectations/great_expectations.conf"),
        "/etc/great_expectations.conf",
    ]

    def __init__(self, runtime_environment: dict):
        """
        Constructor for AbstractDataContext. Will handle instantiation logic that is common to all DataContext objects

        Args:
            runtime_environment (dict): a dictionary of config variables that
                override both those set in config_variables.yml and the environment
        """
        self.runtime_environment = runtime_environment

    @abstractmethod
    def _init_variables(self) -> None:
        raise NotImplementedError

    def _apply_global_config_overrides(
        self, config: Union[DataContextConfig, Mapping]
    ) -> DataContextConfig:

        """
        Applies global configuration overrides for
            - usage_statistics being enabled
            - data_context_id for usage_statistics
            - global_usage_statistics_url

        Args:
            config (DataContextConfig): Config that is passed into the DataContext constructor

        Returns:
            DataContextConfig with the appropriate overrides
        """
        validation_errors: dict = {}
        config_with_global_config_overrides: DataContextConfig = copy.deepcopy(config)
        usage_stats_enabled: bool = self._get_global_usage_statistics_override()
        if not usage_stats_enabled:
            logger.info(
                "Usage statistics is disabled globally. Applying override to project_config."
            )
            config_with_global_config_overrides.anonymous_usage_statistics.enabled = (
                False
            )
        global_data_context_id: Optional[str] = self._get_data_context_id_override()
        # data_context_id
        if global_data_context_id:
            data_context_id_errors = anonymizedUsageStatisticsSchema.validate(
                {"data_context_id": global_data_context_id}
            )
            if not data_context_id_errors:
                logger.info(
                    "data_context_id is defined globally. Applying override to project_config."
                )
                config_with_global_config_overrides.anonymous_usage_statistics.data_context_id = (
                    global_data_context_id
                )
            else:
                validation_errors.update(data_context_id_errors)

        # usage statistics url
        global_usage_statistics_url: Optional[
            str
        ] = self._get_usage_stats_url_override()
        if global_usage_statistics_url:
            usage_statistics_url_errors = anonymizedUsageStatisticsSchema.validate(
                {"usage_statistics_url": global_usage_statistics_url}
            )
            if not usage_statistics_url_errors:
                logger.info(
                    "usage_statistics_url is defined globally. Applying override to project_config."
                )
                config_with_global_config_overrides.anonymous_usage_statistics.usage_statistics_url = (
                    global_usage_statistics_url
                )
            else:
                validation_errors.update(usage_statistics_url_errors)
        if validation_errors:
            logger.warning(
                "The following globally-defined config variables failed validation:\n{}\n\n"
                "Please fix the variables if you would like to apply global values to project_config.".format(
                    json.dumps(validation_errors, indent=2)
                )
            )

        return config_with_global_config_overrides

    @staticmethod
    def _get_global_config_value(
        environment_variable: str,
        conf_file_section: Optional[str] = None,
        conf_file_option: Optional[str] = None,
    ) -> Optional[str]:
        """
        Method to retrieve config value.
        Looks for config value in environment_variable and config file section

        Args:
            environment_variable (str): name of environment_variable to retrieve
            conf_file_section (str): section of config
            conf_file_option (str): key in section

        Returns:
            Optional string representing config value
        """
        assert (conf_file_section and conf_file_option) or (
            not conf_file_section and not conf_file_option
        ), "Must pass both 'conf_file_section' and 'conf_file_option' or neither."
        if environment_variable and os.environ.get(environment_variable, False):
            return os.environ.get(environment_variable)
        if conf_file_section and conf_file_option:
            for config_path in AbstractDataContext.GLOBAL_CONFIG_PATHS:
                config = configparser.ConfigParser()
                config.read(config_path)
                config_value = config.get(
                    conf_file_section, conf_file_option, fallback=None
                )
                if config_value:
                    return config_value
        return None

    @staticmethod
    def _get_global_usage_statistics_override() -> bool:
        """
        Checks environment variable to see if GE_USAGE_STATS exists as an environment variable
        If GE_USAGE_STATS exists AND its value is one of the FALSEY_STRINGS, usage_statistics is disabled (return False)
        Return True otherwise.
        Also checks GLOBAL_CONFIG_PATHS to see if config file contains override for anonymous_usage_statistics
        Returns:
            bool that tells you whether usage_statistics is on or off
        """
        if os.environ.get("GE_USAGE_STATS", False):
            ge_usage_stats = os.environ.get("GE_USAGE_STATS")
            if ge_usage_stats in AbstractDataContext.FALSEY_STRINGS:
                return False
            else:
                logger.warning(
                    "GE_USAGE_STATS environment variable must be one of: {}".format(
                        AbstractDataContext.FALSEY_STRINGS
                    )
                )
        for config_path in AbstractDataContext.GLOBAL_CONFIG_PATHS:
            config = configparser.ConfigParser()
            states = config.BOOLEAN_STATES
            for falsey_string in AbstractDataContext.FALSEY_STRINGS:
                states[falsey_string] = False
            states["TRUE"] = True
            states["True"] = True
            config.BOOLEAN_STATES = states
            config.read(config_path)
            try:
                if config.getboolean("anonymous_usage_statistics", "enabled"):
                    return True
                else:
                    return False
            except (ValueError, configparser.Error):
                pass
        return True

    def _get_data_context_id_override(self) -> Optional[str]:
        """
        Return data_context_id from environment variable.

        Returns:
            Optional string that represents data_context_id
        """
        return self._get_global_config_value(
            environment_variable="GE_DATA_CONTEXT_ID",
            conf_file_section="anonymous_usage_statistics",
            conf_file_option="data_context_id",
        )

    def _get_usage_stats_url_override(self) -> Optional[str]:
        """
        Return GE_USAGE_STATISTICS_URL from environment variable if it exists

        Returns:
            Optional string that represents GE_USAGE_STATISTICS_URL
        """
        return self._get_global_config_value(
            environment_variable="GE_USAGE_STATISTICS_URL",
            conf_file_section="anonymous_usage_statistics",
            conf_file_option="usage_statistics_url",
        )

    ## Public Methods

    def get_config_with_variables_substituted(
        self, config: Optional[DataContextConfig] = None
    ) -> DataContextConfig:
        """
        Substitute vars in config of form ${var} or $(var) with values found in the following places,
        in order of precedence: ge_cloud_config (for Data Contexts in GE Cloud mode), runtime_environment,
        environment variables, config_variables, or ge_cloud_config_variable_defaults (allows certain variables to
        be optional in GE Cloud mode).
        """
        if not config:
            config = self.config

        substitutions: dict = self._determine_substitutions()

    ## Properties
    @property
    @abstractmethod
    def config(self) -> DataContextConfig:
        pass

    @property
    @abstractmethod
    def config(self) -> DataContextConfig:
        pass

    @property
    @abstractmethod
    def config(self) -> DataContextConfig:
        pass

    def _determine_substitutions(self) -> dict:
        """Aggregates substitutions from the project's config variables file, any environment variables, and
        the runtime environment.

        Returns: A dictionary containing all possible substitutions that can be applied to a given object
             using `substitute_all_config_variables`.
        """
        substituted_config_variables: dict = substitute_all_config_variables(
            self.config_variables,
            dict(os.environ),
            self.DOLLAR_SIGN_ESCAPE_STRING,
        )
        substitutions = {
            **substituted_config_variables,
            **dict(os.environ),
            **self.runtime_environment,
        }
        return substitutions

    def _determine_substitutions(self) -> dict:
        """Aggregates substitutions from the project's config variables file, any environment variables, and
        the runtime environment.

        Returns: A dictionary containing all possible substitutions that can be applied to a given object
             using `substitute_all_config_variables`.
        """
        # this is the key difference. In the case of FileDataContex, we will look at the config file
        config: dict = self.config
        substituted_config_variables: dict = substitute_all_config_variables(
            self.config_variables,
            dict(os.environ),
            self.DOLLAR_SIGN_ESCAPE_STRING,
        )
        substitutions = {
            **substituted_config_variables,
            **dict(os.environ),
            **self.runtime_environment,
        }
        return substitutions
