document.addEventListener('DOMContentLoaded', () => {
    const mappingForm = document.getElementById('recon-mapping-form');
    const runButton = document.getElementById('runRecon');
    const cancelButton = document.getElementById('cancelRecon');
    const statusBox = document.getElementById('reconJsonStatus');
    const previewBox = document.getElementById('reconJsonPreview');
    const defaultPreview = 'Select mappings, then choose Run Recon to fetch matches.';
    const downloadBox = document.getElementById('reconDownloadLinks');

    if (!mappingForm) {
        return;
    }

    const setStatus = (message, type = 'info') => {
        if (!statusBox) return;
        statusBox.className = '';
        if (type === 'success') {
            statusBox.classList.add('alert', 'alert-success', 'mb-0');
        } else if (type === 'error') {
            statusBox.classList.add('alert', 'alert-danger', 'mb-0');
        } else {
            statusBox.classList.add('alert', 'alert-secondary', 'mb-0');
        }
        statusBox.textContent = message;
    };

    const csrfToken = () => mappingForm.querySelector('input[name=csrfmiddlewaretoken]')?.value || '';
    const buildFormData = () => new FormData(mappingForm);

    const parseResponse = async (response) => {
        const data = await response.json();
        return { ok: response.ok, data };
    };

    if (runButton) {
        runButton.addEventListener('click', (event) => {
            event.preventDefault();
            const formData = buildFormData();
            setStatus('Running reconciliation...', 'info');

            fetch('/recon/run/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken(),
                },
                body: formData,
            })
                .then(parseResponse)
                .then(({ ok, data }) => {
                    if (!ok) {
                        setStatus(data.message || 'Unable to run reconciliation.', 'error');
                        return;
                    }

                    if (downloadBox) {
                        downloadBox.innerHTML = `
                            <a class="btn btn-success btn-sm" href="${data.download_reconciled_url}" target="_blank">Download Reconciled (${data.reconciled_count})</a>
                            <a class="btn btn-warning btn-sm" href="${data.download_unreconciled_url}" target="_blank">Download Unreconciled (${data.unreconciled_count})</a>
                        `;
                    }
                    if (previewBox) {
                        previewBox.textContent = `Reconciled: ${data.reconciled_count}, Unreconciled: ${data.unreconciled_count}`;
                    }
                    setStatus(data.message || 'Reconciliation complete.', 'success');
                })
                .catch((error) => {
                    console.error('Recon run error', error);
                    setStatus('Unexpected error while running reconciliation.', 'error');
                });
        });
    }

    if (cancelButton) {
        cancelButton.addEventListener('click', (event) => {
            event.preventDefault();
            setStatus('Resetting form...', 'info');

            fetch('/recon/reset/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken(),
                },
            })
                .then(parseResponse)
                .then(() => {
                    mappingForm.reset();
                    if (previewBox) previewBox.textContent = defaultPreview;
                    if (downloadBox) downloadBox.innerHTML = '';
                    setStatus('Cleared. Reloading...', 'success');
                    window.location.reload();
                })
                .catch((error) => {
                    console.error('Recon reset error', error);
                    mappingForm.reset();
                    if (previewBox) previewBox.textContent = defaultPreview;
                    if (downloadBox) downloadBox.innerHTML = '';
                    setStatus('Cleared locally. Please refresh if the file remains loaded.', 'info');
                });
        });
    }
});
