from django.db import models

# Create your models here.
class FileProcessSetting(models.Model):
    SettingId=models.BigAutoField(primary_key=True)
    EndpointAddress=models.CharField(max_length=200,null=True)
    InvalidAccountLedger=models.CharField(max_length=200,null=True)
    EndpointAddress2=models.CharField(max_length=200,null=True)

    Corehost=models.CharField(max_length=200,null=True)
    Coreport=models.CharField(max_length=200,null=True)
    Coredatabase=models.CharField(max_length=200,null=True)
    Coreusername=models.CharField(max_length=200,null=True)
    Corepassword=models.CharField(max_length=200,null=True)
    DefaultODProduct=models.CharField(max_length=200,null=True)
