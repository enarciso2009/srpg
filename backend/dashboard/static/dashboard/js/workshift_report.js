document.addEventListener('DOMContentLoaded', function () {

    console.log('Workshift report carregado');

    const btnLoadReport = document.getElementById('btn-load-report');
    const startDateInput = document.getElementById('start_date');
    const endDateInput = document.getElementById('end_date');
    const reportBody = document.getElementById('report-body');

    const totalDuration = document.getElementById('total-duration');
    const totalDelay = document.getElementById('total-delay');
    const totalExtra = document.getElementById('total-extra');

    btnLoadReport.addEventListener('click', function () {

        const startDate = startDateInput.value;
        const endDate = endDateInput.value;

        if (!startDate || !endDate) {
            alert('Informe a data inicial e final');
            return;
        }

        const url = `/api/attendance/reports/workshift/?start_date=${startDate}&end_date=${endDate}`;

        reportBody.innerHTML = '';
        totalDuration.textContent = '00:00';
        totalDelay.textContent = '00:00';
        totalExtra.textContent = '00:00';

        fetch(url)
            .then(response => response.json())
            .then(data => {
                console.log('Dados recebidos:', data);

                if (!Array.isArray(data.rows)) {
                    console.error('Formato inesperado:', data);
                    return;
                }

                data.rows.forEach(row => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>${row.date}</td>
                        <td>${row.start_time}</td>
                        <td>${row.end_time || '-'}</td>
                        <td>${row.duration}</td>
                        <td>${row.delay}</td>
                        <td>${row.extra}</td>
                        <td>
                            <span class="badge ${row.adjusted ? 'bg-warning text-dark' : 'bg-success'}">
                                ${row.adjusted ? 'Ajustado' : 'OK'}
                            </span>
                        </td>
                    `;
                    reportBody.appendChild(tr);
                });

                totalDuration.textContent = data.totals.total_duration || '00:00';
                totalDelay.textContent = data.totals.total_delay || '00:00';
                totalExtra.textContent = data.totals.total_extra || '00:00';
            })
            .catch(error => {
                console.error(error);
                alert('Erro ao carregar relatório');
            });
    });
});
