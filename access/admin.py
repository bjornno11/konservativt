# access/admin.py
from django.contrib import admin
from .models import Role, RoleAssignment
admin.site.register(Role)
admin.site.register(RoleAssignment)
