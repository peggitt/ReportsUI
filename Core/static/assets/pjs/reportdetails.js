function extractReportErrorMessage(request) {
    try {
        if (request && request.responseJSON) {
            if (request.responseJSON.Exception) return request.responseJSON.Exception;
            if (request.responseJSON.error) return request.responseJSON.error;
            if (request.responseJSON.message) return request.responseJSON.message;
        }
        if (request && request.responseText) {
            var parsed = JSON.parse(request.responseText);
            if (parsed.Exception) return parsed.Exception;
            if (parsed.error) return parsed.error;
            if (parsed.message) return parsed.message;
            return request.responseText;
        }
    } catch (e) {}

    if (request && request.statusText) {
        return request.statusText;
    }
    return "Unable to generate report. Please try again.";
}

function showReportErrorMessage(message) {
    if (window.Swal && typeof window.Swal.fire === "function") {
        window.Swal.fire({
            icon: "error",
            title: "Report Error",
            text: message
        });
        return;
    }
    LoadCollabError(message);
}

function btnviewReport()
{

    var ActionTag = 'ReportView';
    var formId = '#report';
    var csrf = GetInputValue("hdncsrf");
    showBusyPopup();
    $.ajax({
        type: "POST",
        url: "/requestreport/",
        data: $(formId).serialize(),
        success: function(response,request) {
            hideBusyPopup();
            LoadCollabSuccess(response.Success['details']);
            const link = document.createElement('a');
            link.href = response.Success.file_url;
            link.download = '';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        },
        error: function(request) {
            var errMessage = extractReportErrorMessage(request);
            hideBusyPopup();
            showReportErrorMessage(errMessage);
        }
    });
    hidePleaseWait();
}

function btnviewReportxls()
{

    var ActionTag = 'ReportView';
    var formId = '#report';
    var csrf = GetInputValue("hdncsrf");
    showBusyPopup();
    $.ajax({
        type: "POST",
        url: "/requestreportxls/",
        data: $(formId).serialize(),
        success: function(response,request) {
            hideBusyPopup();
            LoadCollabSuccess(response.Success['details']);
            const link = document.createElement('a');
            link.href = response.Success.file_url;
            link.download = '';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        },
        error: function(request) {
            var errMessage = extractReportErrorMessage(request);
            hideBusyPopup();
            showReportErrorMessage(errMessage);
        }
    });
    hidePleaseWait();
}

var reportFieldSearchConfigs = {};
var activeSearchFieldConfig = null;
var activeTargetInput = null;
var searchResultsCache = [];
var reportFieldSearchModal = null;

function normalizeSearchFieldKey(value) {
    return String(value || "").toLowerCase().replace(/[^a-z0-9]/g, "");
}

function escapeHtml(value) {
    return String(value || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/\"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function showLookupError(message) {
    if (window.Swal && typeof window.Swal.fire === "function") {
        window.Swal.fire({ icon: "error", title: "Search Error", text: message });
        return;
    }
    LoadCollabError(message);
}

function clearSearchGrid() {
    $("#reportFieldSearchResults thead").empty();
    $("#reportFieldSearchResults tbody").empty();
    searchResultsCache = [];
    $("#reportSearchResultCount").text("Run a search to view records");
}

function setEmptyGridMessage(message, colSpan) {
    $("#reportFieldSearchResults tbody").html(
        '<tr><td class="text-center" colspan="' + colSpan + '">' + escapeHtml(message) + '</td></tr>'
    );
}

function openReportSearchPopup(inputElement, config) {
    activeTargetInput = inputElement;
    activeSearchFieldConfig = config;

    $("#reportFieldSearchModalLabel").text(config.title || "Search");

    var fieldsHtml = "";
    (config.search_fields || []).forEach(function(field) {
        fieldsHtml += '' +
            '<div class="col-xl-4 col-md-6">' +
            '  <label class="form-label" for="popup-search-' + escapeHtml(field.name) + '">' + escapeHtml(field.label || field.name) + '</label>' +
            '  <input type="text" class="form-control popup-search-input" id="popup-search-' + escapeHtml(field.name) + '" data-field-name="' + escapeHtml(field.name) + '" placeholder="Enter ' + escapeHtml(field.label || field.name) + '">' +
            '</div>';
    });

    $("#reportSearchFieldsContainer").html(fieldsHtml);
    clearSearchGrid();
    setEmptyGridMessage("Enter search criteria above.", 1);

    if (!reportFieldSearchModal) {
        var modalElement = document.getElementById("reportFieldSearchModal");
        reportFieldSearchModal = new bootstrap.Modal(modalElement);
    }
    reportFieldSearchModal.show();
    setTimeout(function() {
        $("#reportSearchFieldsContainer .popup-search-input").first().trigger("focus");
    }, 180);
}

function renderSearchResults(rows, displayColumns) {
    var columns = (displayColumns && displayColumns.length) ? displayColumns.slice() : [];
    if (!columns.length && rows.length) {
        columns = Object.keys(rows[0]);
    }

    if (!columns.length) {
        setEmptyGridMessage("No columns to display.", 1);
        return;
    }

    var headerHtml = "<tr>";
    columns.forEach(function(columnName) {
        headerHtml += "<th>" + escapeHtml(columnName) + "</th>";
    });
    headerHtml += "<th>Action</th></tr>";

    var bodyHtml = "";
    rows.forEach(function(row, idx) {
        bodyHtml += '<tr>';
        columns.forEach(function(columnName) {
            var value = row[columnName];
            bodyHtml += "<td>" + escapeHtml(value == null ? "" : value) + "</td>";
        });
        bodyHtml += '<td><button type="button" class="btn btn-sm btn-outline-theme btn-select-search-row" data-row-index="' + idx + '">Select</button></td>';
        bodyHtml += '</tr>';
    });

    if (!rows.length) {
        bodyHtml = '<tr><td class="text-center" colspan="' + (columns.length + 1) + '">No records found.</td></tr>';
    }

    $("#reportFieldSearchResults thead").html(headerHtml);
    $("#reportFieldSearchResults tbody").html(bodyHtml);
    $("#reportSearchResultCount").text(rows.length === 1 ? "1 record found" : rows.length + " records found");
}

function runConfiguredFieldSearch() {
    if (!activeSearchFieldConfig) {
        return;
    }

    var criteria = {};
    $(".popup-search-input").each(function() {
        var fieldName = $(this).data("field-name");
        criteria[fieldName] = ($(this).val() || "").trim();
    });

    var searchButton = $("#btnRunFieldSearch");
    searchButton.prop("disabled", true).addClass("is-loading");
    searchButton.find("span").text("Searching...");
    $("#reportSearchResultCount").text("Searching records...");

    $.ajax({
        type: "POST",
        url: "/report-field-search/query/",
        contentType: "application/json",
        data: JSON.stringify({
            target_field: activeSearchFieldConfig.field_name,
            criteria: criteria
        }),
        success: function(response) {
            searchResultsCache = response.rows || [];
            renderSearchResults(searchResultsCache, response.display_columns || activeSearchFieldConfig.display_columns || []);
        },
        error: function(request) {
            var message = extractReportErrorMessage(request);
            clearSearchGrid();
            setEmptyGridMessage("Search failed.", 1);
            showLookupError(message || "Unable to search records.");
        },
        complete: function() {
            searchButton.prop("disabled", false).removeClass("is-loading");
            searchButton.find("span").text("Search records");
        }
    });
}

function attachFieldSearchButtons() {
    var textInputs = document.querySelectorAll("#report input[type='text']");
    textInputs.forEach(function(input) {
        if (input.dataset.searchEnhanced === "1") {
            return;
        }

        var normalized = normalizeSearchFieldKey(input.id || input.name);
        var config = reportFieldSearchConfigs[normalized];
        if (!config) {
            return;
        }

        input.dataset.searchEnhanced = "1";

        var parent = input.parentNode;
        var group = document.createElement("div");
        group.className = "input-group";

        parent.insertBefore(group, input);
        group.appendChild(input);

        var button = document.createElement("button");
        button.type = "button";
        button.className = "btn btn-outline-theme report-search-btn";
        button.innerHTML = '<i class="fa fa-search"></i>';
        button.title = config.title || "Search";
        button.addEventListener("click", function() {
            openReportSearchPopup(input, config);
        });

        group.appendChild(button);
    });
}

function initializeFieldSearchLookup() {
    $.ajax({
        type: "GET",
        url: "/report-field-search/config/",
        success: function(response) {
            reportFieldSearchConfigs = response.configs || {};
            attachFieldSearchButtons();
        },
        error: function(request) {
            var message = extractReportErrorMessage(request);
            console.error("Failed to load field-search config:", message);
        }
    });
}

document.addEventListener("DOMContentLoaded", function() {
    initializeFieldSearchLookup();

    $("#btnRunFieldSearch").on("click", function() {
        runConfiguredFieldSearch();
    });

    $(document).on("keydown", "#reportSearchFieldsContainer .popup-search-input", function(event) {
        if (event.key === "Enter") {
            event.preventDefault();
            runConfiguredFieldSearch();
        }
    });

    $(document).on("click", ".btn-select-search-row", function() {
        if (!activeTargetInput || !activeSearchFieldConfig) {
            return;
        }

        var rowIndex = Number($(this).data("row-index"));
        var row = searchResultsCache[rowIndex] || null;
        if (!row) {
            return;
        }

        var valueField = activeSearchFieldConfig.value_field;
        var value = row[valueField];

        if (value == null) {
            var keys = Object.keys(row);
            if (keys.length) {
                value = row[keys[0]];
            }
        }

        activeTargetInput.value = value == null ? "" : value;
        $(activeTargetInput).trigger("change");

        if (reportFieldSearchModal) {
            reportFieldSearchModal.hide();
        }
    });
});
