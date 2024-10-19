import React from "react";
import ChartComponent from "./ChartComponent";
import Layout from "./Layout";

const DailyProductionPage = () => {
  return (
    <Layout>
      <ChartComponent
        intervalOptions={["daily", "monthly", "yearly"]}
        buttonNames={["Daily", "Monthly", "Yearly"]}
        fetchDataEndpoint={"/api/data"}
        dateSelectorEnable={true}
        fifteenData={false}
      />
    </Layout>
  );
};

export default DailyProductionPage;
