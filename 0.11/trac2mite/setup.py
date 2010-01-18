"""
SetupTrac2Mite:
plugin to enable the environment for Trac2mite.
This plugin must be initialized prior to using Trac2mite

Modified version of plugin SetupTracHoursPlugin
"""

from trac.core import *
from trac.db import Table, Column, Index, DatabaseManager
from trac.env import IEnvironmentSetupParticipant

from tracsqlhelper import *


class SetupTrac2Mite(Component):

    implements(IEnvironmentSetupParticipant)

    ### methods for IEnvironmentSetupParticipant

    """Extension point interface for components that need to participate in the
    creation and upgrading of Trac environments, for example to create
    additional database tables."""
        

    def environment_created(self):
        """Called when a new Trac environment is created."""
        if self.environment_needs_upgrade(None):
            self.upgrade_environment(None)

    def environment_needs_upgrade(self, db):
        """Called when Trac checks whether the environment needs to be upgraded.
        
        Should return `True` if this participant needs an upgrade to be
        performed, `False` otherwise.
        """
        version = self.version()
        return version < len(self.steps)

    def upgrade_environment(self, db):
        """Actually perform an environment upgrade.
        
        Implementations of this method should not commit any database
        transactions. This is done implicitly after all participants have
        performed the upgrades they need without an error being raised.
        """
        if not self.environment_needs_upgrade(db):
            return

        version = self.version()
        for version in range(self.version(), len(self.steps)):
            for step in self.steps[version]:
                step(self)
        execute_non_query(self.env, "update system set value='%s' where name='trac2mite.db_version';" % len(self.steps))


    ### helper methods

    def version(self):
        """returns version of the database (an int)"""
        version = get_scalar(self.env, "select value from system where name = 'trac2mite.db_version';")
        if version:
            return int(version)
        return 0


    ### upgrade steps

    def create_plugin_tables(self):
        mite_bindings_table = Table('mite_bindings', key=('id'))[
            Column('id', auto_increment=True),
            Column('user'),
			Column('mite_rsrc_id', type='int'),
			Column('component_id', type='int')
            ]
        create_table(self.env, mite_bindings_table)
		
        mite_rsrcs_table = Table('mite_rsrcs', key=('id'))[
            Column('id', auto_increment=True),
            Column('user'),
			Column('remote_rsrc_id', type='int'),
			Column('type'),
			Column('name')
            ]
        create_table(self.env, mite_rsrcs_table)
		
        mite_user_prefs_table = Table('mite_user_prefs', key=('user'))[
            Column('user'),
            Column('account_name'),
            Column('api_key'),
            Column('note_pattern'),
            Column('connection_updated_on', type='int')
            ]
        create_table(self.env, mite_user_prefs_table)
		
        execute_non_query(self.env, "insert into system (name, value) values ('trac2mite.db_version', '1');")

    def add_fields_to_ticket_time_table(self):
        execute_non_query(self.env, "ALTER TABLE 'ticket_time' ADD 'mite_time_entry_id' INT( 11 );")
        execute_non_query(self.env, "ALTER TABLE 'ticket_time' ADD 'mite_project_id' INT( 11 );")
        execute_non_query(self.env, "ALTER TABLE 'ticket_time' ADD 'mite_service_id' INT( 11 );")
        execute_non_query(self.env, "ALTER TABLE 'ticket_time' ADD 'mite_time_entry_updated_on' INT( 11 );")
			
    # ordered steps for upgrading
    steps = [ [ create_plugin_tables, add_fields_to_ticket_time_table], # version 1
            ]
