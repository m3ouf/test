class PhysicalAdslRouter(object):
    def db_for_read(self, model, **hints):
        if model._meta.app_label == 'physical_adsl_backend':
            return 'physical_adsl'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == 'physical_adsl_backend':
            return 'physical_adsl'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        if obj1._meta.app_label == 'physical_adsl_backend' or \
           obj2._meta.app_label == 'physical_adsl_backend':
           return True
        return None

    def allow_syncdb(self, db, model):
        if db == 'physical_adsl':
            return model._meta.app_label == 'physical_adsl_backend'
        elif model._meta.app_label == 'physical_adsl_backend':
            return False
        return None