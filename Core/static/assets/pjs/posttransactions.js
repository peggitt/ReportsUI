function postUploadedData(fileType) {
    var ModuleId = 'FileProcessing';
    var ActionTag = 'Post_' + fileType;
    var csrf = GetInputValue("hdncsrf");
    showBusyPopup();
    $.ajax({
        type: "POST",
        url: "/posttransactions/",
        data: 'ActionID=' + ActionTag + '&ModuleId=' + ModuleId + '&file_type=' + fileType,
        success: function(response, request) {
            hideBusyPopup();

            if(response.FileStatus === 'true')
                window.location.href = '/PassedTransaction/';
            else    
                window.location.href = '/failedtransaction/';
        },
        error: function(request) {
            hideBusyPopup();
            try{
                var ErrJson = JSON.parse(request.responseText);
                if(ErrJson.message)
                    LoadCollabInfo(ErrJson.message);
                else if(request.status === 404)
                    LoadCollabError(ErrJson.Exception);
                else
                    LoadCollabInfo(ErrJson.Exception);
            }catch(e){
                LoadCollabInfo('Unable to process the selected file type.');
            }
        }
    });
    hidePleaseWait();
}

function btnPostTransactions() {
    postUploadedData('transactionsfile');
}
