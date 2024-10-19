import React, { useState, useEffect } from "react";

async function fetchAlerts() {
  try {
    const response = await fetch("/alerts");
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error fetching data:", error);
    return {};
  }
}

function SiteAlerts() {
  const [data, setData] = useState({});
  const [nonZeroSites, setNonZeroSites] = useState([]);

  useEffect(() => {
    fetchAlerts().then((responseData) => {
      setData(responseData);
      const nonZeroSitesSorted = Object.keys(responseData)
        .filter((site) => responseData[site] !== 0)
        .sort((a, b) => responseData[b] - responseData[a]);
      setNonZeroSites(nonZeroSitesSorted);
    });
  }, []);

  return (
    <div>
      <div className="flex-grow flex flex-wrap">
        {nonZeroSites.map((siteName) => (
          <div key={siteName} className="bg-white rounded-lg shadow-md p-2 m-1">
            <div>
              <h3 className="font-semibold">Site Name:</h3>
              <p className="text-gray-700">{siteName}</p>
            </div>
            <div>
              <h3 className="font-semibold">Consecutive Zero Production Days:</h3>
              <p className="text-gray-700">{data[siteName]}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default SiteAlerts;
