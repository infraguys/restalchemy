#    Copyright 2025 Genesis Corporation.
#
#    All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


from oslo_config import cfg

from restalchemy.common import constants as c


CONF = cfg.CONF


def register_common_db_opts(
    conf,
    connection_url=None,
    config_section=c.DB_CONFIG_SECTION,
):
    """
    Registers common database options

    :param conf: Config instance
    :param connection_url: default connection url
    :param config_section: section name to register options in
    """
    db_opt = [
        cfg.StrOpt(
            name="connection_url",
            default=connection_url,
            help="Connection URL to db",
        ),
        cfg.BoolOpt(
            "connection_query_cache",
            default=True,
            help="Cache queries to the database within the transaction",
        ),
        cfg.StrOpt(
            "migrations_path",
            default="migrations",
            help="Path to db migrations",
        ),
        cfg.BoolOpt(
            "apply_migrations_on_startup",
            default=True,
            help="Apply migrations on startup",
        ),
    ]

    conf.register_cli_opts(db_opt, group=config_section)


def register_posgresql_db_opts(
    conf=CONF,
    username=c.RA_POSTGRESQL_USERNAME,
    password=c.RA_POSTGRESQL_PASSWORD,
    host=c.RA_POSTGRESQL_DB_HOST,
    port=c.RA_POSTGRESQL_DB_PORT,
    db_name=c.RA_POSTGRESQL_DB_NAME,
    config_section=c.DB_CONFIG_SECTION,
):
    """
    Registers the configuration options required for a PostgreSQL DB connection.

    This includes the common database options and specific options for the
    PostgreSQL connection pool such as minimum and maximum pool size, connection
    timeout, and other pool management options.

    :param conf: The configuration object to register the options with.
    :param username: The username to use for the connection.
    :param password: The password to use for the connection.
    :param host: The host to connect to.
    :param port: The port to connect to.
    :param db_name: The name of the database to connect to.
    :param config_section: The configuration section to register the options in.
    """

    proto = c.RA_POSTGRESQL_PROTO_NAME
    connection_url = f"{proto}://{username}:{password}@{host}:{port}/{db_name}"

    register_common_db_opts(
        conf=conf,
        connection_url=connection_url,
        config_section=config_section,
    )

    db_opt = [
        cfg.IntOpt(
            name="connection_pool_min_size",
            default=1,
            help=(
                "The minimum number of connection the pool will hold. The"
                " pool will actively try to create new connections if some"
                " are lost (closed, broken) and will try to never go below"
                " min_size"
            ),
        ),
        cfg.IntOpt(
            name="connection_pool_max_size",
            default=2,
            help=(
                "The maximum number of connections the pool will hold. If"
                " None, or equal to min_size, the pool will not grow or"
                " shrink. If larger than min_size, the pool can grow if more"
                " than min_size connections are requested at the same time"
                " and will shrink back after the extra connections have been"
                " unused for more than max_idle seconds."
            ),
        ),
        cfg.BoolOpt(
            "connection_pool_open",
            default=True,
            help=(
                " If True, open the pool, creating the required connections,"
                " on init. If False, open the pool when open() is called"
                " or when the pool context is entered. See the open() method"
                " documentation for more details."
            ),
        ),
        cfg.FloatOpt(
            "connection_pool_client_timeout",
            default=30.0,
            help=(
                "The default maximum time in seconds that a client can wait"
                " to receive a connection from the pool (using connection()"
                " or getconn()). Note that these methods allow to override"
                " the timeout default."
            ),
        ),
        cfg.IntOpt(
            "connection_pool_max_waiting",
            default=10,
            help=(
                "Maximum number of requests that can be queued to the pool,"
                " after which new requests will fail, raising"
                " TooManyRequests. 0 means no queue limit."
            ),
        ),
        cfg.FloatOpt(
            "connection_max_lifetime",
            default=3600.0,
            help=(
                "The maximum lifetime of a connection in the pool, in"
                " seconds. Connections used for longer get closed and"
                " replaced by a new one. The amount is reduced by a"
                " random 10% to avoid mass eviction."
            ),
        ),
        cfg.FloatOpt(
            "connection_max_idle",
            default=600.0,
            help=(
                "Maximum time, in seconds, that a connection can stay"
                " unused in the pool before being closed, and the pool"
                " shrunk. This only happens to connections more than"
                " min_size, if max_size allowed the pool to grow."
            ),
        ),
        cfg.FloatOpt(
            "connection_pool_reconnect_timeout",
            default=300.0,
            help=(
                "Maximum time, in seconds, the pool will try to create"
                " a connection. If a connection attempt fails, the pool"
                " will try to reconnect a few times, using an exponential"
                " backoff and some random factor to avoid mass attempts."
                " If repeated attempts fail, after reconnect_timeout second"
                " the connection attempt is aborted and the"
                " reconnect_failed() callback invoked."
            ),
        ),
        cfg.IntOpt(
            "connection_pool_num_workers",
            default=1,
            help=(
                "Number of background worker threads used to maintain the"
                " pool state. Background workers are used for example to"
                " create new connections and to clean up connections when"
                " they are returned to the pool."
            ),
        ),
    ]

    conf.register_cli_opts(db_opt, config_section)


def register_mysql_db_opts(
    conf=CONF,
    username=c.RA_MYSQL_USERNAME,
    password=c.RA_MYSQL_PASSWORD,
    host=c.RA_MYSQL_DB_HOST,
    port=c.RA_MYSQL_DB_PORT,
    db_name=c.RA_MYSQL_DB_NAME,
    config_section=c.DB_CONFIG_SECTION,
):
    """
    Registers the configuration options required for a MySQL DB connection.

    These are as follows:

    - connection_pool_size: The number of connection the pool will hold.

    :param conf: The configuration object to register the options with.
    :param username: The username to use for the connection.
    :param password: The password to use for the connection.
    :param host: The host to connect to.
    :param port: The port to connect to.
    :param db_name: The name of the database to connect to.
    :param config_section: The configuration section to register the options in.
    """
    proto = c.RA_MYSQL_PROTO_NAME
    connection_url = f"{proto}://{username}:{password}@{host}:{port}/{db_name}"

    register_common_db_opts(
        conf=conf,
        connection_url=connection_url,
        config_section=config_section,
    )

    db_opt = [
        cfg.IntOpt(
            name="connection_pool_size",
            default=1,
            help=(
                "The number of connection the pool will hold. The"
                " pool will actively try to create new connections if some"
                " are lost (closed, broken) and will try to never go below"
                " size"
            ),
        ),
    ]

    conf.register_cli_opts(db_opt, config_section)
