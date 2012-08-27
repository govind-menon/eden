# -*- coding: utf-8 -*-

"""
    Admin Controllers
"""

module = request.controller
resourcename = request.function

# S3 framework functions
# -----------------------------------------------------------------------------
def index():

    """ Module's Home Page """

    module_name = deployment_settings.modules[module].name_nice
    response.title = module_name
    return dict(module_name=module_name)


# =============================================================================
@auth.s3_requires_membership(1)
def setting():
    """ Custom page to link to those Settings which can be edited through the web interface """
    return dict()

# =============================================================================
# AAA
# =============================================================================
@auth.s3_requires_membership(1)
def role():
    """
        Role Manager

        @author: Dominic König <dominic@aidiq.com>
    """

    module = "auth"
    name = "group"

    # ACLs as component of roles
    s3db.add_component(auth.permission.table,
                       auth_group="group_id")

    def prep(r):
        if r.representation != "html":
            return False
        handler = s3base.S3RoleManager()
        modules = deployment_settings.modules
        handler.controllers = Storage([(m, modules[m])
                                        for m in modules
                                        if modules[m].restricted])
        # Configure REST methods
        r.set_handler("users", handler)
        r.set_handler("read", handler)
        r.set_handler("list", handler)
        r.set_handler("copy", handler)
        r.set_handler("create", handler)
        r.set_handler("update", handler)
        r.set_handler("delete", handler)
        return True
    s3.prep = prep

    s3.stylesheets.append( "S3/role.css" )
    output = s3_rest_controller(module, name)
    return output

# -----------------------------------------------------------------------------
@auth.s3_requires_membership(1)
def user():
    """ RESTful CRUD controller """

    tablename = "auth_user"
    table = db[tablename]
    
    auth.configure_user_fields()

    s3db.configure(tablename,
                   main="first_name",
                   # Only needed if image & mobile fields get added to admin user form
                   #create_onaccept = auth.s3_user_create_onaccept,
                   # This is called from the Link action button
                   # update_onaccept = auth.s3_user_onaccept,
                   )

    def disable_user(r, **args):
        if not r.id:
            session.error = T("Can only disable 1 record at a time!")
            redirect(URL(args=[]))

        if r.id == session.auth.user.id: # we're trying to disable ourself
            session.error = T("Cannot disable your own account!")
            redirect(URL(args=[]))

        table = auth.settings.table_user
        query = (table.id == r.id)
        db(query).update(registration_key = "disabled")
        session.confirmation = T("User Account has been Disabled")
        redirect(URL(args=[]))

    def approve_user(r, **args):
        if not r.id:
            session.error = T("Can only approve 1 record at a time!")
            redirect(URL(args=[]))
        
        user = table[r.id]
        auth.s3_approve_user(user)

        session.confirmation = T("User Account has been Approved")
        redirect(URL(args=[]))
        
    def link_user(r, **args):
        if not r.id:
            session.error = T("Can only update 1 record at a time!")
            redirect(URL(args=[]))
        
        user = table[r.id]
        auth.s3_link_user(user)

        session.confirmation = T("User has been (re)linked to Person and Human Resource record")
        redirect(URL(args=[]))

    # Custom Methods
    role_manager = s3base.S3RoleManager()
    set_method = s3db.set_method
    set_method("auth", "user", method="roles",
               action=role_manager)

    set_method("auth", "user", method="disable",
               action=disable_user)

    set_method("auth", "user", method="approve",
               action=approve_user)
    
    set_method("auth", "user", method="link",
               action=link_user)

    # CRUD Strings
    ADD_USER = T("Add User")
    s3.crud_strings[tablename] = Storage(
        title_create = ADD_USER,
        title_display = T("User Details"),
        title_list = T("Users"),
        title_update = T("Edit User"),
        title_search = T("Search Users"),
        subtitle_create = T("Add New User"),
        label_list_button = T("List Users"),
        label_create_button = ADD_USER,
        label_delete_button = T("Delete User"),
        msg_record_created = T("User added"),
        msg_record_modified = T("User updated"),
        msg_record_deleted = T("User deleted"),
        msg_list_empty = T("No Users currently registered"))

    def rheader(r, tabs = []):
        if not r.interactive or r.representation != "html":
            return None
        
        id = r.id
        
        rheader = DIV()
        
        if r.record:
            registration_key = r.record.registration_key
            if not registration_key:
                btn = A(T("Disable"),
                        _class = "action-btn",
                        _title = "Disable User",
                        _href = URL(args=[id,
                                          "disable"]
                                    )
                        )
                rheader.append(btn)
                btn = A(T("Link"),
                        _class = "action-btn",
                        _title = "Link (or refresh link) between User, Person & HR Record",
                        _href = URL(args=[id,
                                          "link"]
                                    )
                        )
                rheader.append(btn)
                
            if registration_key == "pending":
                btn = A(T("Approve"),
                        _class = "action-btn",
                        _title = "Approve User",
                        _href = URL(args=[id,
                                          "approve"]
                                    )
                        )
                rheader.append(btn)

            tabs = [ (T("User Details"), None),
                     (T("Roles"), "roles")]
            rheader_tabs = s3_rheader_tabs(r, tabs)
            rheader.append(rheader_tabs)
        return rheader

    # Pre-processor
    def prep(r):
        if r.interactive:
            s3db.configure(r.tablename,
                           deletable=False,
                           # jquery.validate is clashing with dataTables so don't embed the create form in with the List
                           listadd=False,
                           addbtn=True,
                           sortby = [[2, "asc"], [1, "asc"]],
                           # Password confirmation
                           create_onvalidation = user_create_onvalidation)

            # Add specifc buttons to enable/disable users
            # Allow the ability for admin to Disable logins
            #reg = r.table.registration_key
            #reg.writable = True
            #reg.readable = True
            #reg.label = T("Status")
            # In Controller to allow registration to work with UUIDs - only manual edits need this setting
            #reg.requires = IS_NULL_OR(IS_IN_SET(["disabled",
            #                                     "pending"]))

        elif r.representation == "aadata":
            # dataTables' columns need to match
            r.table.registration_key.readable = True

        if r.method == "delete" and r.http == "GET":
            if r.id == session.auth.user.id: # we're trying to delete ourself
                request.get_vars.update({"user.id":str(r.id)})
                r.id = None
                s3db.configure(r.tablename,
                               delete_next = URL(c="default", f="user/logout"))
                s3.crud.confirm_delete = T("You are attempting to delete your own account - are you sure you want to proceed?")

        if r.http == "GET" and not r.method:
            session.s3.cancel = r.url()
        return True
    s3.prep = prep

    def postp(r, output):
        # Only show the disable button if the user is not currently disabled
        query = (r.table.registration_key != "disabled") & \
                (r.table.registration_key != "pending")
        rows = db(query).select(r.table.id)
        restrict = [str(row.id) for row in rows]
        s3.actions = [
                        dict(label=str(UPDATE), _class="action-btn",
                             url=URL(c="admin", f="user",
                                     args=["[id]", "update"])),
                        dict(label=str(T("Link")), 
                             _class="action-btn",
                             _title = str(T("Link (or refresh link) between User, Person & HR Record")),
                             url=URL(c="admin", f="user",
                                     args=["[id]", "link"])),
                        dict(label=str(T("Roles")), _class="action-btn",
                             url=URL(c="admin", f="user",
                                     args=["[id]", "roles"])),
                        dict(label=str(T("Disable")), _class="action-btn",
                             url=URL(c="admin", f="user",
                                     args=["[id]", "disable"]),
                             restrict = restrict)
                      ]
        # Only show the approve button if the user is currently pending
        query = (r.table.registration_key == "pending")
        rows = db(query).select(r.table.id)
        restrict = [str(row.id) for row in rows]
        s3.actions.append(
                dict(label=str(T("Approve")), _class="action-btn",
                     url=URL(c="admin", f="user",
                             args=["[id]", "approve"]),
                     restrict = restrict)
            )
        # Add some highlighting to the rows
        rtable = r.table
        query = (rtable.registration_key.belongs(["disabled", "pending"]))
        rows = db(query).select(rtable.id,
                                rtable.registration_key)
        s3.dataTableStyleDisabled = s3.dataTableStyleWarning = [str(row.id) for row in rows if row.registration_key == "disabled"]
        s3.dataTableStyleAlert = [str(row.id) for row in rows if row.registration_key == "pending"]

        # Add client-side validation
        s3base.s3_register_validation()

        return output
    s3.postp = postp

    def registration_key_represent(value):
        if value == "disabled":
            return str(T("Disabled"))
        elif value == "pending":
            return str(T("Pending"))
        else:
            return str(T("Active"))
    table.registration_key.represent = registration_key_represent
    output = s3_rest_controller("auth", resourcename, rheader = rheader)
    return output

# =============================================================================
def group():
    """
        RESTful CRUD controller
        - used by role_required autocomplete
    """

    tablename = "auth_group"

    if not auth.s3_has_role(ADMIN):
        s3db.configure(tablename,
                       editable=False,
                       insertable=False,
                       deletable=False)

    # CRUD Strings
    ADD_ROLE = T("Add Role")
    s3.crud_strings[tablename] = Storage(
        title_create = ADD_ROLE,
        title_display = T("Role Details"),
        title_list = T("Roles"),
        title_update = T("Edit Role"),
        title_search = T("Search Roles"),
        subtitle_create = T("Add New Role"),
        label_list_button = T("List Roles"),
        label_create_button = ADD_ROLE,
        msg_record_created = T("Role added"),
        msg_record_modified = T("Role updated"),
        msg_record_deleted = T("Role deleted"),
        msg_list_empty = T("No Roles currently defined"))

    s3db.configure(tablename, main="role")
    return s3_rest_controller("auth", resourcename)

# -----------------------------------------------------------------------------
@auth.s3_requires_membership(1)
def organisation():
    """
        RESTful CRUD controller

        @ToDo: Prevent multiple records for the same domain
    """

    module = "auth"
    tablename = "auth_organisation"
    table = s3db[tablename]

    s3.crud_strings[tablename] = Storage(
        title_create = T("Add Organization Domain"),
        title_display = T("Organization Domain Details"),
        title_list = T("Organization Domains"),
        title_update = T("Edit Organization Domain"),
        title_search = T("Search Organization Domains"),
        subtitle_create = T("Add New Organization Domain"),
        label_list_button = T("List Organization Domains"),
        label_create_button = T("Add Organization Domain"),
        label_delete_button = T("Delete Organization Domain"),
        msg_record_created = T("Organization Domain added"),
        msg_record_modified = T("Organization Domain updated"),
        msg_record_deleted = T("Organization Domain deleted"),
        msg_list_empty = T("No Organization Domains currently registered")
    )

    output = s3_rest_controller(module, resourcename)

    return output

# -----------------------------------------------------------------------------
def user_create_onvalidation (form):
    """ Server-side check that Password confirmation field is valid """
    if (form.request_vars.has_key("password_two") and \
        form.request_vars.password != form.request_vars.password_two):
        form.errors.password = T("Password fields don't match")
    return True

# =============================================================================
@auth.s3_requires_membership(1)
def acl():
    """
        Preliminary controller for ACLs
        for testing purposes, not for production use!
    """

    module = "s3"
    name = "permission"

    table = auth.permission.table
    tablename = table._tablename
    table.group_id.requires = IS_ONE_OF(db, "auth_group.id", "%(role)s")
    table.group_id.represent = lambda opt: opt and db.auth_group[opt].role or opt

    table.controller.requires = IS_EMPTY_OR(IS_IN_SET(auth.permission.modules.keys(),
                                                      zero="ANY"))
    table.controller.represent = lambda opt: opt and \
        "%s (%s)" % (opt,
                     auth.permission.modules.get(opt, {}).get("name_nice", opt)) or "ANY"

    table.function.represent = lambda val: val and val or T("ANY")

    table.tablename.requires = IS_EMPTY_OR(IS_IN_SET([t._tablename for t in db],
                                                     zero=T("ANY")))
    table.tablename.represent = lambda val: val and val or T("ANY")

    table.uacl.label = T("All Resources")
    table.uacl.widget = S3ACLWidget.widget
    table.uacl.requires = IS_ACL(auth.permission.PERMISSION_OPTS)
    table.uacl.represent = lambda val: acl_represent(val,
                                                     auth.permission.PERMISSION_OPTS)

    table.oacl.label = T("Owned Resources")
    table.oacl.widget = S3ACLWidget.widget
    table.oacl.requires = IS_ACL(auth.permission.PERMISSION_OPTS)
    table.oacl.represent = lambda val: acl_represent(val,
                                                     auth.permission.PERMISSION_OPTS)

    s3db.configure(tablename,
                   create_next = URL(r=request),
                   update_next = URL(r=request))

    if "_next" in request.vars:
        next = request.vars._next
        s3db.configure(tablename, delete_next=next)

    output = s3_rest_controller(module, name)
    return output


# -----------------------------------------------------------------------------
def acl_represent(acl, options):
    """
        Represent ACLs in tables
        for testing purposes, not for production use!
    """

    values = []

    for o in options.keys():
        if o == 0 and acl == 0:
            values.append("%s" % options[o][0])
        elif acl and acl & o == o:
            values.append("%s" % options[o][0])
        else:
            values.append("_")

    return " ".join(values)

# =============================================================================
# Ticket viewing
# =============================================================================
@auth.s3_requires_membership(1)
def ticket():
    """ Ticket handler """

    import traceback
    from gluon.restricted import RestrictedError

    if len(request.args) != 2:
        session.error = T("Invalid ticket")
        redirect(URL(r=request))

    app = request.args[0]
    ticket = request.args[1]
    e = RestrictedError()
    e.load(request, app, ticket)

    return dict(app=app,
                ticket=ticket,
                traceback=s3base.Traceback(e.traceback),
                code=e.code,
                layer=e.layer)

# -----------------------------------------------------------------------------
# Web2Py Ticket Viewer functions Borrowed from admin application of web2py
@auth.s3_requires_membership(1)
def errors():
    """ Error handler """

    from gluon.admin import apath
    from gluon.fileutils import listdir

    for item in request.vars:
        if item[:7] == "delete_":
            os.unlink(apath("%s/errors/%s" % (appname, item[7:]), r=request))

    func = lambda p: os.stat(apath("%s/errors/%s" % (appname, p), r=request)).st_mtime
    tickets = sorted(listdir(apath("%s/errors/" % appname, r=request), "^\w.*"),
                     key=func,
                     reverse=True)

    return dict(app=appname, tickets=tickets)

# =============================================================================
# Create portable app
# =============================================================================
@auth.s3_requires_membership(1)
def portable():
    """ Portable app creator"""

    from gluon.admin import apath
    import os
    from operator import itemgetter, attrgetter

    uploadfolder=os.path.join(apath("%s" % appname, r=request), "cache")
    web2py_source = None
    web2py_source_exists = False
    last_build_exists = False

    for base, dirs, files in os.walk(uploadfolder):
        for filename in files:
            if "web2py_source" in filename:
                web2py_source_exists = True
                web2py_source = filename
                break

    for base, dirs, files in os.walk(uploadfolder):
        for filename in files:
            if "download.zip" in filename:
                last_build_exists = True
                break

    web2py_form = SQLFORM.factory(
            Field("web2py_source",
                  "upload",
                  uploadfolder=uploadfolder,
                  requires=IS_UPLOAD_FILENAME(extension="zip"),
                ),
            table_name="web2py_source",
            )

    if web2py_form.accepts(request.vars, keepvalues=True, session=None):
        # Make sure only one web2py source file exists
        files_to_remove = {}
        for base, dirs, files in os.walk(uploadfolder):
            for filename in files:
                if "web2py_source" in filename:
                    files_to_remove[filename] = os.stat(os.path.join(uploadfolder, filename)).st_mtime
        sorted_files = sorted(files_to_remove.items(), key=itemgetter(1))
        for i in range(0, len(sorted_files) - 1): # 1 indicates leave one file
            os.remove(os.path.join(uploadfolder,sorted_files[i][0]))
        web2py_source = sorted_files[len(sorted_files) - 1][0]
        web2py_source_exists = True
        session.flash = T("Web2py executable zip file found - Upload to replace the existing file")
    else:
        # Lets throw an error message if this the zip file isn't found
        if not web2py_source_exists:
            session.error = T("Web2py executable zip file needs to be uploaded to use this function.")
        else:
            session.flash = T("Web2py executable zip file found - Upload to replace the existing file")

    generator_form = SQLFORM.factory(
            Field("copy_database", "boolean"),
            Field("copy_uploads", "boolean"),
            )

    if generator_form.accepts(request.vars, keepvalues=True, session=None):
        if web2py_source_exists:
            create_portable_app(web2py_source=web2py_source,\
                    copy_database = request.vars.copy_database,\
                    copy_uploads = request.vars.copy_uploads)
        else:
            session.error = T("Web2py executable zip file needs to be uploaded to use this function.")
    if last_build_exists:
        download_last_form = SQLFORM.factory()
        if download_last_form.accepts(request.vars, keepvalues=True, session=None):
            portable_app = os.path.join(cachedir, "download.zip")
            response.headers["Content-Type"] = contenttype.contenttype(portable_app)
            response.headers["Content-Disposition"] = \
                    "attachment; filename=portable-sahana.zip"
            return response.stream(portable_app)

    else:
        download_last_form = None
    return dict(
            web2py_form=web2py_form,
            generator_form=generator_form,
            download_last_form=download_last_form
        )

# -----------------------------------------------------------------------------
def create_portable_app(web2py_source, copy_database=False, copy_uploads=False):
    """Function to create the portable app based on the parameters"""

    from gluon.admin import apath
    import shutil,tempfile,os
    import zipfile
    import contenttype

    cachedir = os.path.join(apath("%s" % appname, r=request), "cache")
    tempdir = tempfile.mkdtemp("", "eden-", cachedir)
    workdir = os.path.join(tempdir, "web2py")
    if copy_uploads:
        ignore = shutil.ignore_patterns("*.db", "*.log", "*.table", "errors", "sessions", "compiled" , "cache", ".bzr", "*.pyc")
    else:
        ignore = shutil.ignore_patterns("*.db", "*.log", "*.table", "errors", "sessions", "compiled" , "uploads", "cache", ".bzr", "*.pyc")

    appdir = os.path.join(workdir, "applications", appname)
    shutil.copytree(apath("%s" % appname, r=request),\
                    appdir, \
                    ignore = ignore)
    os.mkdir(os.path.join(appdir, "errors"))
    os.mkdir(os.path.join(appdir, "sessions"))
    os.mkdir(os.path.join(appdir, "cache"))
    if not copy_uploads:
        os.mkdir(os.path.join(appdir, "uploads"))

    shutil.copy(os.path.join(appdir, "deployment-templates", "cron", "crontab"),\
            os.path.join(appdir, "cron", "crontab"))

    if copy_database:
        # Copy the db for the portable app
        s3db.load_all_models() # Load all modules to copy everything

        portable_db = DAL("sqlite://storage.db", folder=os.path.join(appdir, "databases"))
        for table in db:
            portable_db.define_table(table._tablename, *[field for field in table])

        portable_db.commit()

        temp_csv_file=tempfile.mkstemp()
        db.export_to_csv_file(open(temp_csv_file[1], "wb"))
        portable_db.import_from_csv_file(open(temp_csv_file[1], "rb"))
        os.unlink(temp_csv_file[1])
        portable_db.commit()

    # Replace the following with a more specific config
    config_template = open(os.path.join(appdir, "deployment-templates", "models", "000_config.py"), "r")
    new_config = open(os.path.join(appdir, "models", "000_config.py"), "w")
    # Replace first occurance of False with True
    new_config.write(config_template.read().replace("False", "True", 1))
    new_config.close()

    # Embedded the web2py source with eden for download
    shutil.copy(os.path.join(cachedir, web2py_source), os.path.join(cachedir, "download.zip"))
    portable_app = os.path.join(cachedir, "download.zip")
    zip = zipfile.ZipFile(portable_app, "a", zipfile.ZIP_DEFLATED)
    tozip = os.path.join(tempdir, "web2py")
    rootlen = len(tempdir) + 1

    for base, dirs, files in os.walk(tozip):
        for directory in dirs:
            directory = os.path.join(base, directory)
            zip.write(directory, directory[rootlen:]) # Create empty directories
        for file in files:
            fn = os.path.join(base, file)
            zip.write(fn, fn[rootlen:])

    zip.close()
    shutil.rmtree(tempdir)
    response.headers["Content-Type"] = contenttype.contenttype(portable_app)
    response.headers["Content-Disposition"] = \
                            "attachment; filename=portable-sahana.zip"

    return response.stream(portable_app)

# END =========================================================================
