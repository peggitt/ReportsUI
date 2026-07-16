from django.db import models
from django.utils import timezone

class ReportFile(models.Model):
    ReportId=models.BigAutoField(primary_key=True)
    ReportGroup=models.CharField(max_length=200,null=True)
    ReportName=models.CharField(max_length=200,null=True)
    ReportDescription=models.CharField(max_length=1000,null=True)
    SPObjectName=models.CharField(max_length=1000,null=True)
    isActive = models.BooleanField(default = True)
    Top1Left=models.CharField(max_length=1000,null=True,default='',blank=True)
    Top2Left=models.CharField(max_length=1000,null=True,default='',blank=True)
    Top3Left=models.CharField(max_length=1000,null=True,default='',blank=True)
    Top4Left=models.CharField(max_length=1000,null=True,default='',blank=True)
    Top5Left=models.CharField(max_length=1000,null=True,default='',blank=True)
    Top1Right=models.CharField(max_length=1000,null=True,default='',blank=True)
    Top2Right=models.CharField(max_length=1000,null=True,default='',blank=True)
    Top3Right=models.CharField(max_length=1000,null=True,default='',blank=True)
    Top4Right=models.CharField(max_length=1000,null=True,default='',blank=True)
    Top5Right=models.CharField(max_length=1000,null=True,default='',blank=True)

    Botto1Left=models.CharField(max_length=1000,null=True,default='',blank=True)
    Bottom2Left=models.CharField(max_length=1000,null=True,default='',blank=True)
    Bottom3Left=models.CharField(max_length=1000,null=True,default='',blank=True)
    Bottom4Left=models.CharField(max_length=1000,null=True,default='',blank=True)
    Bottom5Left=models.CharField(max_length=1000,null=True,default='',blank=True)
    Bottom1Right=models.CharField(max_length=1000,null=True,default='',blank=True)
    Bottom2Right=models.CharField(max_length=1000,null=True,default='',blank=True)
    Bottom3Right=models.CharField(max_length=1000,null=True,default='',blank=True)
    Bottom4Right=models.CharField(max_length=1000,null=True,default='',blank=True)
    Bottom5Right=models.CharField(max_length=1000,null=True,default='',blank=True)

    def __str__(self):
        report_name = (self.ReportName or "").strip()
        if report_name:
            return f"{self.ReportId} - {report_name}"
        return str(self.ReportId)

class ReportFileDetail(models.Model):
    ReportDetailId=models.BigAutoField(primary_key=True)
    ReportId = models.ForeignKey(ReportFile, on_delete=models.CASCADE)
    FilterName=models.CharField(max_length=200,null=True)
    FilterType=models.CharField(max_length=1000,null=True)
    isActive = models.BooleanField(default = True)

    def __str__(self):
        filter_name = (self.FilterName or "").strip()
        if filter_name:
            return f"{self.ReportId} - {filter_name}"
        return str(self.ReportId)


class ReportColumnDefinition(models.Model):
    LOAD_SIDE_CHOICES = (
        ("LEFT", "Left"),
        ("RIGHT", "Right"),
    )

    ReportColumnId = models.BigAutoField(primary_key=True)
    ReportId = models.ForeignKey(ReportFile, on_delete=models.CASCADE)
    ColumnName = models.CharField(max_length=200, null=False)
    DisplayName = models.CharField(max_length=200, null=True, blank=True)
    DataType = models.CharField(max_length=100, null=True, blank=True)
    ColumnWidth = models.FloatField(null=True, blank=True)
    LoadSide = models.CharField(max_length=10, choices=LOAD_SIDE_CHOICES, default="LEFT")
    SortOrder = models.IntegerField(default=0)
    isVisible = models.BooleanField(default=True)

    class Meta:
        ordering = ["SortOrder", "ReportColumnId"]

    def __str__(self):
        return f"{self.ReportId.ReportName} - {self.ColumnName}"
