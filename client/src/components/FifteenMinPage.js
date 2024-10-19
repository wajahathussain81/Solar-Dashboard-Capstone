import React from "react";
import ChartComponent from "./ChartComponent";
import Layout from "./Layout";

const FifteenMinPage = () => {
  return (
    <Layout>
      <ChartComponent
        intervalOptions={["15T", "H", "12H"]}
        buttonNames={["15 Min", "Hourly", "12 Hour"]}
        fetchDataEndpoint={"/api/15min/data"}
        dateSelectorEnable={false}
        fifteenData={true}
      />
    </Layout>
  );
};

export default FifteenMinPage;
