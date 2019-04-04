from . import config
from .choices import InitializationTypes
from .exceptions import ImproperlyConfigured
from .listeners import IniestaListener
from .utils import filter_list_to_filter_policies


class _Iniesta(object):

    def __init__(self):
        self.config_imported = False
        self.initialization_type = None

    def __getattribute__(self, item):
        if item.startswith('init_'):
            if self.initialization_type is not None:
                raise ImproperlyConfigured('Iniesta has already been initialized!')
        return super().__getattribute__(item)

    def set_initialization_type(self, value):
        if self.initialization_type is None:
            self.initialization_type = value
        else:
            self.initialization_type = self.initialization_type | value


    def check_global_arn(self, settings_object):
        if settings_object.INIESTA_SNS_PRODUCER_GLOBAL_TOPIC_ARN is None:
            raise ImproperlyConfigured("INIESTA_SNS_PRODUCER_GLOBAL_TOPIC_ARN not set in settings!")


    def load_config(self, settings_object):
        if not self.config_imported:
            for c in dir(config):
                if c.isupper():
                    conf = getattr(config, c)
                    if c == "INIESTA_CACHE":
                        settings_object.INSANIC_CACHES.update(conf)
                    elif not hasattr(settings_object, c):
                        setattr(settings_object, c, conf)

            self.config_imported = True

    def init_app(self, app):
        self._init_producer_and_polling(app)

    def _init_producer_and_polling(self, app):
        """

        :param app:
        :return:
        """
        self._init_producer(app)
        self._init_event_polling(app)

    def init_producer(self, app):
        self._init_producer(app)

    def _init_producer(self, app):
        """
        check if global arn is set
        load configs

        :param app:
        :return:
        """
        self.load_config(app.config)

        if not app.config.INIESTA_DRY_RUN:
            # check if global arn exists
            self.check_global_arn(app.config)

            listener = IniestaListener()
            app.register_listener(listener.after_server_start_producer_check,
                                  'after_server_start')
        self.set_initialization_type(InitializationTypes.SNS_PRODUCER)

    def init_queue_polling(self, app):
        self._init_queue_polling(app)

    def _init_queue_polling(self, app):
        """
        Basic sqs queue polling without the need for checking subscriptions
        load configs
        attach listeners to check if queue exists

        :param app:
        :return:
        """
        self.load_config(app.config)
        if not app.config.INIESTA_DRY_RUN:
            listener = IniestaListener()
            app.register_listener(listener.after_server_start_start_queue_polling,
                                  'after_server_start')
            app.register_listener(listener.before_server_stop_stop_polling,
                                  'before_server_stop')
        self.set_initialization_type(InitializationTypes.QUEUE_POLLING)

    def init_event_polling(self, app):
        self._init_event_polling(app)

    def _init_event_polling(self, app):
        """
        # check if global arn exists
        # need to check if filters are 0 to avoid receiving all messages
        # load configs

        - from listeners
        check if queue exists (initialize)
        check subscriptions
        check permissions

        :param app:
        :return:
        """
        self.load_config(app.config)
        if not app.config.INIESTA_DRY_RUN:
            # check if global arn exists
            self.check_global_arn(app.config)

            # check if filters are 0
            if len(app.config.INIESTA_SQS_CONSUMER_FILTERS) == 0:
                raise ImproperlyConfigured("INIESTA_SQS_CONSUMER_FILTERS is an empty list. "
                                           "Please specifiy events to receive!")

            listener = IniestaListener()

            app.register_listener(listener.after_server_start_event_polling,
                                  'after_server_start')
            app.register_listener(listener.before_server_stop_stop_polling,
                                  'before_server_stop')
        self.set_initialization_type(InitializationTypes.EVENT_POLLING)

    def prepare_for_delivering_through_pass(self, app):
        """
        equivalent of init_producer

        :param app:
        :return:
        """
        self.init_producer(app)

    def prepare_for_receiving_short_pass(self, app):
        self.init_queue_polling(app)

    def prepare_for_receiving_through_pass(self, app):
        self.init_event_polling(app)

    def prepare_for_passing_and_receiving(self, app):
        self.init_app(app)

    def filter_policies(self):
        from insanic.conf import settings
        return filter_list_to_filter_policies(
            settings.INIESTA_SNS_EVENT_KEY,
            settings.INIESTA_SQS_CONSUMER_FILTERS)


Iniesta = _Iniesta()