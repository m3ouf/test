import binascii
import os
from django.contrib.auth.models import User
from django.db import models
from datetime import datetime, timedelta


class Token(models.Model):
    user = models.ForeignKey(User)
    token = models.CharField(max_length=40, primary_key=True)
    created = models.DateTimeField(auto_now_add=True)
    expires = models.DateTimeField()

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = self.generate_token()
            self.expires = datetime.now() + timedelta(days=3)
        return super(Token, self).save(*args, **kwargs)

    def generate_token(self):
        return binascii.hexlify(os.urandom(20)).decode()

    def __unicode__(self):
        return self.token