from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class VaultConfig(AppConfig):
    name = 'vault'
    verbose_name = _("Vault")
