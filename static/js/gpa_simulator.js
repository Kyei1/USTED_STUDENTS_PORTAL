(function () {
    const payloadNode = document.getElementById("gpa-ui-data");
    if (!payloadNode || typeof Chart === "undefined") {
        return;
    }

    let data;
    try {
        data = JSON.parse(payloadNode.textContent);
    } catch (error) {
        return;
    }

    const maroon = "#7a0016";
    const gold = "#dba111";

    const comparisonCtx = document.getElementById("comparisonChart");
    if (comparisonCtx) {
        new Chart(comparisonCtx, {
            type: "bar",
            data: {
                labels: ["Baseline SGPA", "Projected SGPA", "Baseline CGPA", "Projected CGPA"],
                datasets: [
                    {
                        label: "Score",
                        data: [
                            data.single.baselineSgpa,
                            data.single.projectedSgpa,
                            data.single.baselineCgpa,
                            data.single.projectedCgpa,
                        ],
                        backgroundColor: ["rgba(122,0,22,0.72)", "rgba(219,161,17,0.85)", "rgba(122,0,22,0.5)", "rgba(219,161,17,0.58)"],
                        borderColor: [maroon, gold, maroon, gold],
                        borderWidth: 1.3,
                        borderRadius: 8,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 4,
                        ticks: { stepSize: 0.5 },
                    },
                },
            },
        });
    }

    const historyCtx = document.getElementById("historyChart");
    if (historyCtx) {
        new Chart(historyCtx, {
            type: "line",
            data: {
                labels: data.history.labels,
                datasets: [
                    {
                        label: "CGPA Trend",
                        data: data.history.values,
                        borderColor: maroon,
                        backgroundColor: "rgba(122,0,22,0.1)",
                        pointBackgroundColor: gold,
                        pointBorderColor: maroon,
                        pointRadius: 4,
                        borderWidth: 2,
                        tension: 0.35,
                        fill: true,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 4,
                        ticks: { stepSize: 0.5 },
                    },
                },
            },
        });
    }
})();
