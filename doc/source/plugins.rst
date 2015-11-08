..
      Copyright 2015 Hewlett-Packard Development Company, L.P.
      All Rights Reserved.

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

.. _searchlight-plugins:

Searchlight Plugin Documentation
================================

The search service determines the types of information that is searchable
via a plugin mechanism.

Installing Plugins
------------------

Plugins must be registered in ``setup.cfg``.

Within ``setup.cfg`` the setting within ``[entry_points]`` named
``searchlight.index_backend`` should list the plugin for each available
indexable type. After making a change, it's necessary to re-install the
python package (for instance with ``pip install -e .``).

Each plugin registered in ``setup.cfg`` is enabled by default. Typically it
should only be necessary to modify ``setup.cfg`` if you are installing a new
plugin. It is not necessary to modify ``[entry_points]`` to temporarily
enable or disable installed plugins. Once they are installed, they can be
disabled, enabled and configured in the ``searchlight-api.conf`` file.

Configuring Plugins
-------------------

After installation, plugins are configured in ``searchlight-api.conf``.

.. note::

    After making changes to ``searchlight-api.conf`` you must perform the
    actions indicated in the tables below.

    1. ``Restart services``: Restart all running ``searchlight-api`` *and*
       ``searchlight-listener`` processes.

    2. ``Re-index affected types``: You will need to re-index any resource
       types affected by the change. (See :doc:`indexingservice`).

.. note::

    Unless you are changing to a non-default value, you do not need to
    specify any of the following configuration options.

.. _end-to-end-plugin-configuration-example:

End to End Configuration Example
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The following shows a sampling of various configuration options in
``searchlight-api.conf``. These are **NOT** necessarily recommended
or default configuration values. They are intended for exemplary purposes only.
Please read the rest of the guide for detailed information.::

    [resource_plugin]
    index_name = searchlight

    [resource_plugin:os_server_nova]
    index_name = nova
    enabled = True
    unsearchable_fields = OS-EXT-SRV*,OS-EXT-STS:vm_state

    [resource_plugin:os_glance_image]
    enabled = True

    [resource_plugin:os_glance_metadef]
    enabled = True

    [resource_plugin:os_designate_zone]
    enabled = False

    [resource_plugin:os_designate_recordset]
    enabled = False


Common Plugin Configuration Options
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

There are common configuration options that all plugins honor. They are split
between *inheritable* options and *non-inheritable* options.

**Inheritable** common configuration options may be specified in a default
configuration group of ``[resource_plugin]`` in ``searchlight-api.conf`` and
optionally overridden in a specific plugin's configuration. For example::

    [resource_plugin]
    index_name = searchlight

    [resource_plugin:os_nova_server]
    index_name = nova

**Non-Inheritable** common configuration options are honored by all plugins,
but must be specified directly in that plugin's configuration group. They are
are not inherited from the ``[resource_plugin]`` configuration group. For
example::

    [resource_plugin:os_glance_image]
    enabled = false

See :ref:`individual-plugin-configuration` for more information and examples
on individual plugin configuration.

Inheritable Common Configuration Options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

+---------------------+---------------+-------------------------------------+---------------------------+
| Option              | Default value | Description                         | Action(s) Required        |
+=====================+===============+=====================================+===========================+
| index_name          | searchlight   | The ElasticSearch index where the   | | Restart services        |
|                     |               | plugin resource documents will be   | | Re-index affected types |
|                     |               | stored in. It is recommended to not |                           |
|                     |               | change this unless needed.          |                           |
+---------------------+---------------+-------------------------------------+---------------------------+

Non-Inheritable Common Configuration Options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

+---------------------+---------------+-------------------------------------+---------------------------+
| Option              | Default value | Description                         | Action(s) Required        |
+=====================+===============+=====================================+===========================+
| enabled             | true          | An installed plugin may be enabled  | | Restart services        |
|                     |               | (true) or disabled (false). When    | | Re-index affected types |
|                     |               | disabled, it will not be available  |                           |
|                     |               | for bulk indexing, notification     |                           |
|                     |               | listening, or searching.            |                           |
+---------------------+---------------+-------------------------------------+---------------------------+
| unsearchable_fields | <none>        | A comma separated list of fields    | | Restart services        |
|                     |               | (wildcards allowed) that are stored | | Re-index affected types |
|                     |               | in ElasticSearch, but can not be    |                           |
|                     |               | searched on regardless of the       |                           |
|                     |               | user's role (admin or not).         |                           |
|                     |               | The fields will still be returned   |                           |
|                     |               | in search results for admin users,  |                           |
|                     |               | but not normal users. These fields  |                           |
|                     |               | are typically specified for search  |                           |
|                     |               | performance, search accuracy,       |                           |
|                     |               | or security reasons.                |                           |
|                     |               | If a plugin has a hard-coded        |                           |
|                     |               | mapping for a specific field, it    |                           |
|                     |               | will take precedence over this      |                           |
|                     |               | configuration option.               |                           |
+---------------------+---------------+-------------------------------------+---------------------------+

.. _individual-plugin-configuration:

Individual Plugin Configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Individual plugins may also be configured in  ``searchlight-api.conf``.

.. note::

    Plugin configurations are typically named based on their resource type.
    The configuration name uses the following naming pattern:

    * The resource type name changed to all lower case

    * All ``::`` (colons) converted into ``_`` (underscores).

    For example: OS::Glance::Image --> [resource_plugin:os_glance_image]

To override a default configuration option on a specific plugin, you must
specify a configuration group for that plugin with the option(s) that you
want to override. For example, if you wanted to **just** disable the Glance
image plugin, you would add the following configuration group::

    [resource_plugin:os_glance_image]
    enabled = false

Each plugin may have additional configuration options specific to it.
Information about those configuration options will be found in documentation
for that plugin.

Finally, each integrated service (Glance, Nova, etc) may require
additional configuration settings. For example, typically, you will need
to add the ``searchlight_indexer`` notification topic to each service's
configuration in order for Searchlight to receive incremental updates from
that service.

Please review each plugin's documentation for more information:

.. toctree::
   :maxdepth: 1
   :glob:

   plugins/*
