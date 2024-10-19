import React, { useEffect, useRef, useState } from "react";
import Chart from "chart.js/auto";
import { Line, Bar } from "react-chartjs-2";
import "chartjs-adapter-date-fns";
import zoomPlugin from "chartjs-plugin-zoom";
import moment from "moment";
import axios from "axios";
import SiteFilterTab from "./SiteFilterTab";

const ChartComponent = ({
  intervalOptions,
  buttonNames,
  fetchDataEndpoint,
  dateSelectorEnable,
  fifteenData,
}) => {
  const [data, setData] = useState(null);
  const [selectedSites, setSelectedSites] = useState([]);
  const [startDate, setStartDate] = useState(
    moment().subtract(1, "years").format("YYYY-MM-DD")
  );
  const [endDate, setEndDate] = useState(new Date());
  const [selection, setSelection] = useState(intervalOptions[0]);

  Chart.register(zoomPlugin);
  const handleIntervalChange = (value) => {
    setSelection(value);
  };

  useEffect(() => {
    let intervalId;

    const fetchData = async () => {
      try {
        const response = await axios.post(fetchDataEndpoint, { selection });
        setData(response.data || []);
      } catch (error) {
        console.error("Error:", error);
      }
    };

    if (fifteenData) {
      // Fetch data initially
      fetchData();
      // Set up the interval for periodic data fetch only if fifteenData is true
      intervalId = setInterval(fetchData, 15 * 60 * 1000); // 15 minutes in milliseconds
    } else {
      fetchData();
    }

    // Cleanup function to clear the interval
    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [selection, fetchDataEndpoint, fifteenData]); // Include fifteenData in dependencies

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      x: {
        type: "time",
        time: {
          parser: fifteenData ? "yyyy-MM-dd HH:mm:ss" : "yyyy-MM-dd",
          unit: fifteenData ? "hour" : "day",
          displayFormats: {
            hour: "yyyy-MM-dd HH:mm:ss",
            day: "yyyy-MM-dd",
          },
        },
        ticks: {
          autoSkip: true,
        },
      },
      y: {
        beginAtZero: true,
        title: {
            display: true,
            text: "Production (kWh)"}
      },
    },
    plugins: {
      legend: {
        display: true,
        position: "right",
        align: "start",
      },
      zoom: {
        zoom: {
          wheel: { enabled: true },
          pinch: { enabled: true },
          mode: "x",
        },
        pan: {
          enabled: true,
          mode: "x",
        },
      },
    },
  };

  const updateChart = () => {
    if (!data || typeof data !== "object" || Object.keys(data).length === 0) {
      return { labels: [], datasets: [] };
    }

    let allDates = new Set();

    const datasets = selectedSites.map((site) => {
      const siteData = (data[site] || []).filter((record) => {
        if (!fifteenData) {
          // Apply date filtering only when fifteenData is false
          const recordDate = moment(record.Date);
          // Adjust to ensure start date is included from the start of the day and end date till the end of the day
          const startOfDay = moment(startDate).startOf("day");
          const endOfDay = moment(endDate).endOf("day");
          return recordDate.isBetween(startOfDay, endOfDay, null, "[]");
        }
        return true; // Include all data if fifteenData is true
      });

      siteData.forEach((record) => {
        allDates.add(
          moment(record.Date).format(
            fifteenData ? "yyyy-MM-DD HH:mm:ss" : "YYYY-MM-DD"
          )
        );
      });

      return {
        label: site,
        data: siteData.map((record) => ({
          x: moment(record.Date).format(
            fifteenData ? "yyyy-MM-DD HH:mm:ss" : "YYYY-MM-DD"
          ),
          y: record["Production (kWh)"],
        })),
        borderColor: getRandomColor(),
        borderWidth: 2,
        tension: 0.4,
        fill: true,
      };
    });

    const labels = Array.from(allDates).sort(
      (a, b) => new Date(a) - new Date(b)
    );
    return { labels, datasets };
  };

  const handleDownload = () => {
    if (data && selectedSites.length > 0) {
      const allSitesCombined = {};
      const siteWiseProduction = {};

      let date_format;
      if (fifteenData) {
        date_format = "yyyy-MM-DD HH:mm:ss";
      } else {
        date_format = "yyyy-MM-DD";
      }

      selectedSites.forEach((site) => {
        const siteData = data[site] || [];

        // Explicitly initialize if not already done
        if (!siteWiseProduction[site]) {
          siteWiseProduction[site] = {};
        }

        siteData.forEach((item) => {
          const date = moment(item.Date).format(date_format);
          const production = parseFloat(item["Production (kWh)"]);
          siteWiseProduction[site][date] =
            (siteWiseProduction[site][date] || 0) + production;

//          console.log("Site wise:",siteWiseProduction[site][date], "Production wise:", production)
          allSitesCombined[date] = (allSitesCombined[date] || 0) + siteWiseProduction[site][date];
//          console.log("Before parse float All site:", allSitesCombined[date], "on", date)

        });
      });


      let filteredDates;
      if (fifteenData) {
        filteredDates = Object.keys(allSitesCombined);
      } else {
        filteredDates = Object.keys(allSitesCombined).filter((date) =>
          moment(date).isBetween(startDate, endDate, null, "[]")
        );
      }

//      console.log(siteWiseProduction);
      let csvContent = "Date";
      selectedSites.forEach((site) => {
        csvContent += `,${site} (kWh)`;
      });
      csvContent += ",All Sites (kWh)\n";

      filteredDates.forEach((date) => {
        let rowData = `${date}`;
        selectedSites.forEach((site) => {
          rowData += `,${siteWiseProduction[site][date] || 0}`;
        });
        rowData += `,${allSitesCombined[date]}`;
        csvContent += `${rowData}\n`;
      });

      const blob = new Blob([csvContent], { type: "text/csv" });
      const url = URL.createObjectURL(blob);

      const a = document.createElement("a");
      a.href = url;
      a.download = "Production_data.csv";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    }
  };

const getRandomColor = () => {
    const letters = "0123456789ABCDEF";
    const randomComponent1 = Math.floor(Math.random() * 8).toString(16); // Generating first random component
    const randomComponent2 = Math.floor(Math.random() * 8).toString(16); // Generating second random component
    const randomComponent3 = Math.floor(Math.random() * 8).toString(16); // Generating third random component
    return `#${randomComponent1}${randomComponent1}${randomComponent2}${randomComponent2}${randomComponent3}${randomComponent3}`;
};

  const IntervalSelection = ({ selection, handleIntervalChange }) => {
    return (
      <>
        {intervalOptions.map((option, index) => (
          <button
            key={option}
            className={`${
              selection === option
                ? "bg-[#c8102e]" // Active button background color
                : "bg-[#5d6066]" // Default button background color
            } text-white border-0 py-2.5 px-5 mr-1 mb-2.5 cursor-pointer rounded-md transition-colors`}
            onClick={() => handleIntervalChange(option)}
          >
            {buttonNames[index]}
          </button>
        ))}
      </>
    );
  };

  return (
    <>
      <SiteFilterTab
        selectedSites={selectedSites}
        setSelectedSites={setSelectedSites}
        startDate={startDate}
        setStartDate={setStartDate}
        endDate={endDate}
        setEndDate={setEndDate}
        dateSelectorEnable={dateSelectorEnable}
        fifteenData={fifteenData}
      />
      <div className="flex flex-col flex-grow overflow-y-auto px-4 py-4">
        <div className="flex mb-4">
          <IntervalSelection
            selection={selection}
            handleIntervalChange={handleIntervalChange}
          />
          <button
            className="ml-auto py-2.5 px-5 text-base bg-red-700 text-white border-0 rounded-md cursor-pointer transition shadow-md"
            onClick={handleDownload}
          >
            Download Data
          </button>
        </div>
        <div className="w-full h-full md:h-full">
          <Line id="chart" options={chartOptions} data={updateChart()} />
        </div>
      </div>
    </>
  );
};

export default ChartComponent;
