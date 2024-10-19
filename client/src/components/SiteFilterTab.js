import React, { useEffect, useState } from "react";
import axios from "axios";
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";
import { ChevronRightIcon, ChevronDownIcon } from "@heroicons/react/24/solid";

const DateRangeSelection = ({
  startDate,
  endDate,
  handleStartDateChange,
  handleEndDateChange,
}) => (
  <div className="flex flex-col mb-2">
    <h1 className="text-2xl font-bold justify-start">Date Range:</h1>
    <DatePicker
      selected={startDate}
      onChange={handleStartDateChange}
      selectsStart
      startDate={startDate}
      endDate={endDate}
      placeholderText="Start Date"
      className="border rounded px-2 py-1 my-2"
      showYearDropdown
    />
    <label className="font-semibold">To:</label>
    <DatePicker
      selected={endDate}
      onChange={handleEndDateChange}
      selectsEnd
      startDate={startDate} // Used for highlighting the start date in the range
      endDate={endDate}
      minDate={startDate} // Prevents the end date from being before the start date
      placeholderText="End Date"
      className="border rounded px-2 py-1 my-2"
      showYearDropdown
    />
  </div>
);

const SiteFilterTab = ({
  selectedSites,
  setSelectedSites,
  startDate,
  setStartDate,
  endDate,
  setEndDate,
  dateSelectorEnable,
  fifteenData,
}) => {
  const [siteName, setSiteName] = useState([]);
  const [dropdownVisible, setDropdownVisible] = useState({});

  useEffect(() => {
    const fetchData = async () => {
      try {
        let response;
        if (fifteenData) {
          response = await axios.get("/api/site_filter/fifteen");
        } else {
          response = await axios.get("/api/site_filter/daily");
        }
        setSiteName(response.data);
        let initialDropdownState = {};
        response.data.forEach((item) => {
          initialDropdownState[item.manufacturer_name] = false;
        });
        setDropdownVisible(initialDropdownState);
      } catch (error) {
        console.error("Error fetching site data:", error);
      }
    };
    fetchData();
  }, [fifteenData]);

  const handleStartDateChange = (date) => {
    setStartDate(date);
  };

  const handleEndDateChange = (date) => {
    setEndDate(date);
  };

  const toggleDropdown = (manufacturer_name) => {
    setDropdownVisible((prevState) => ({
      ...prevState,
      [manufacturer_name]: !prevState[manufacturer_name],
    }));
  };

  const toggleAllSites = (manufacturer_name) => {
    const manufacturerData = siteName.find(
      (item) => item.manufacturer_name === manufacturer_name
    );
    const allSitesSelected = manufacturerData.sites.every((site) =>
      selectedSites.includes(site)
    );

    if (allSitesSelected) {
      setSelectedSites((prevSites) =>
        prevSites.filter((site) => !manufacturerData.sites.includes(site))
      );
    } else {
      setSelectedSites((prevSites) => [
        ...prevSites,
        ...manufacturerData.sites.filter((site) => !prevSites.includes(site)),
      ]);
    }
  };

  return (
    <div className="flex flex-col flex-none w-64 overflow-y-auto bg-coc-secondary-10L px-5 py-10 border-r-4 border-coc-secondary-8L">
      {dateSelectorEnable && (
        <DateRangeSelection
          startDate={startDate}
          endDate={endDate}
          handleStartDateChange={handleStartDateChange}
          handleEndDateChange={handleEndDateChange}
        />
      )}
      <h1 className="text-2xl font-bold mb-4 justify-start">Manufacturers</h1>
      {siteName.map((item, index) => (
        <div key={index} className="mb-4">
          <div
            className="cursor-pointer flex justify-between items-center"
            onClick={() => toggleDropdown(item.manufacturer_name)}
          >
            <div className="flex items-center">
              <input
                type="checkbox"
                checked={item.sites.every((site) =>
                  selectedSites.includes(site)
                )}
                onClick={(e) => {
                  e.stopPropagation(); // Prevent dropdown toggle
                  toggleAllSites(item.manufacturer_name);
                }}
                className="form-checkbox h-4 w-4"
              />
              <span
                className={`ml-2 ${
                  dropdownVisible[item.manufacturer_name] ? "font-bold" : ""
                }`}
              >
                {item.manufacturer_name}
              </span>
            </div>
            {dropdownVisible[item.manufacturer_name] ? (
              <ChevronDownIcon className="h-5 w-5" />
            ) : (
              <ChevronRightIcon className="h-5 w-5" />
            )}
          </div>
          {dropdownVisible[item.manufacturer_name] && (
            <ul className="ml-6">
              {item.sites.map((site, siteIndex) => (
                <li key={siteIndex} className="flex items-center">
                  <input
                    type="checkbox"
                    checked={selectedSites.includes(site)}
                    onChange={() =>
                      setSelectedSites((prevSites) =>
                        prevSites.includes(site)
                          ? prevSites.filter((s) => s !== site)
                          : [...prevSites, site]
                      )
                    }
                    className="form-checkbox h-4 w-4"
                  />
                  <span className="ml-2">{site}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      ))}
    </div>
  );
};

export default SiteFilterTab;
