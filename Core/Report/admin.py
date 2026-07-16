from django.contrib import admin

from .models import ReportFile, ReportFileDetail, ReportColumnDefinition
admin.site.register(ReportFile)


@admin.register(ReportFileDetail)
class ReportFileDetailAdmin(admin.ModelAdmin):
    list_display = ("ReportId", "FilterName", "FilterType", "isActive")
    list_filter = ("ReportId", "FilterType", "isActive")
    search_fields = ("ReportId__ReportName", "FilterName", "FilterType")


@admin.register(ReportColumnDefinition)
class ReportColumnDefinitionAdmin(admin.ModelAdmin):
    list_display = (
        "ReportId",
        "ColumnName",
        "DisplayName",
        "DataType",
        "ColumnWidth",
        "LoadSide",
        "SortOrder",
        "isVisible",
    )
    list_filter = ("ReportId", "isVisible")
    search_fields = ("ReportId__ReportName", "ColumnName", "DisplayName", "DataType", "LoadSide")
# Register your models here.
