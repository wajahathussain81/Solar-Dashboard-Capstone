import React, { useEffect, useState } from "react";
import axios from "axios";
import { RiLoader4Line } from "react-icons/ri";
import SiteFilterTab from "./SiteFilterTab";

const DateRangeCard = ({ dateRange }) => {
  const rename_values = {
    last_7_days: "Last 7 Days",
    month_to_date: "Month To Date",
    last_month: "Last Month",
    three_month: "Three Months",
    six_month: "Six Months",
    last_year: "Last Year",
    ytd: "Year to Date",
    size_kw: "Site Size",
    Last_Year_Prod_Over_Site_Size_KW: "Last Year's Efficiency",
  };

  return (
    <div className="max-w-sm rounded overflow-hidden shadow-lg my-2">
      <div className="px-6 py-4">
        {Object.entries(dateRange).map(([key, value], index) => (
          <h3
            key={index}
            className="text-grey_coc font-bold text-xl text-center"
          >
            {rename_values[key]}: {value}
          </h3>
        ))}
      </div>
    </div>
  );
};

const CardList = ({ data }) => {
  return (
    <div>
      {data.map((site_data, siteIndex) => (
        <React.Fragment key={siteIndex}>
          <h2 className="text-xl font-bold my-4">{site_data.site}</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {site_data.date_range.map((dateRangeItem, dateRangeIndex) => (
              <DateRangeCard key={dateRangeIndex} dateRange={dateRangeItem} />
            ))}
          </div>
        </React.Fragment>
      ))}
    </div>
  );
};

const Metrics = () => {
  const [totalProduction, setTotalProduction] = useState(null);
  const [selectedSites, setSelectedSites] = useState([]);
  const [startDate, setStartDate] = useState(new Date());
  const [endDate, setEndDate] = useState(new Date());

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await axios.get("/api/aggregated-production");
        setTotalProduction(response.data);
      } catch (error) {
        console.error("Error fetching total production:", error);
      }
    };
    fetchData();
  }, []);

  const filteredData =
    totalProduction?.filter((item) => selectedSites.includes(item.site)) || [];

  return (
    <>
      <SiteFilterTab
        selectedSites={selectedSites}
        setSelectedSites={setSelectedSites}
        startDate={startDate}
        setStartDate={setStartDate}
        endDate={endDate}
        setEndDate={setEndDate}
        dateSelectorEnable={false}
        fifteenData={false}
      />
      <div className="flex-grow px-4 py-4 overflow-y-auto">
        <h1 className="text-3xl font-bold mb-8">Metrics</h1>
        {totalProduction ? (
          <CardList data={filteredData} />
        ) : (
          <div className="flex items-center justify-center h-full">
            <RiLoader4Line className="animate-spin text-blue-500 text-4xl" />
          </div>
        )}
      </div>
    </>
  );
};

export default Metrics;
