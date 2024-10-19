import React from "react";
import { Link, useLocation } from "react-router-dom";

const navigation = [
  {
    name: "Live Data",
    href: "/ProductionData_fifteen",
    current: false,
  },
  {
    name: "Historical Data",
    href: "/ProductionData_daily",
    current: true,
  },
  { name: "Metrics", href: "/Metrics", current: false },
  { name: "Alerts", href: "/Alerts", current: false },
];

const Navbar = () => {
  const location = useLocation();

  function classNames(...classes) {
    return classes.filter(Boolean).join(" ");
  }

  return (
    <nav className="bg-coc-secondary-9L p-6 flex justify-between items-center">
      <div className="mx-5">
        <Link key="Main Home" to="/">
          <img src="/coc-logo.svg" alt="coc-logo" className="h-20" />
        </Link>
      </div>
      <div className="flex-grow justify-items-start mx-5">
        <h1 className="font-bold text-4xl">
          The City of Calgary Solar Dashboard
        </h1>
      </div>
      <div className="hidden md:flex items-center space-x-4">
        {navigation.map((item) => (
          <Link
            key={item.name}
            to={item.href}
            className={classNames(
              item.href === location.pathname
                ? "bg-coc-secondary-2L text-white"
                : "text-black hover:bg-coc-secondary-2L hover:text-white",
              "rounded-md px-3 py-2 text-md font-bold"
            )}
            aria-current={item.href === location.pathname ? "page" : undefined}
          >
            {item.name}
          </Link>
        ))}
      </div>
    </nav>
  );
};

export default Navbar;
