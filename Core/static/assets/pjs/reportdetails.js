function btnviewReport()
{

    var ActionTag = 'ReportView';
    var formId = '#report'; // Change this to the ID of the form you want to submit
    var csrf = GetInputValue("hdncsrf");
    showBusyPopup();
    $.ajax({
        type: "POST",
        url: "/requestreport/",
        data: $(formId).serialize() ,
        success: function(response,request) {
            hideBusyPopup();
            LoadCollabSuccess(response.Success['details']);
            const link = document.createElement('a');
            link.href = response.Success.file_url;  // URL to download the file
            link.download = '';  // Optional: specify a filename
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            //setTimeout(function() {
            //    location.reload();
            //    }, 3000);
            
        },
        error: function(request) {
            var ErrJson = JSON.parse(request.responseText);
            hideBusyPopup();
            if(request.status === 404)
                LoadCollabError(ErrJson.Exception);
            else
                LoadCollabInfo(ErrJson.Exception);

        }
    });
    hidePleaseWait();
}

function btnviewReportxls()
{

    var ActionTag = 'ReportView';
    var formId = '#report'; // Change this to the ID of the form you want to submit
    var csrf = GetInputValue("hdncsrf");
    showBusyPopup();
    $.ajax({
        type: "POST",
        url: "/requestreportxls/",
        data: $(formId).serialize() ,
        success: function(response,request) {
            hideBusyPopup();
            LoadCollabSuccess(response.Success['details']);
            const link = document.createElement('a');
            link.href = response.Success.file_url;  // URL to download the file
            link.download = '';  // Optional: specify a filename
            document.body.appendChild(link)
;
            link.click();
            document.body.removeChild(link)
;
            //setTimeout(function() {
            //    location.reload();
            //    }, 3000);
            
        },
        error: function(request) {
            var ErrJson = JSON.parse(request.responseText);
            hideBusyPopup();
            if(request.status === 404)
                LoadCollabError(ErrJson.Exception);
            else
                LoadCollabInfo(ErrJson.Exception);

        }
    });
    hidePleaseWait();
}