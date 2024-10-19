import React from "react";
import Navbar from "./Navbar.js";
import Footer from "./Footer.js";
import { motion } from "framer-motion";

const Layout = ({ children }) => {
  return (
    <motion.div className="flex flex-col h-screen">
      <Navbar className="flex-shrink-0" />
      <div className="flex flex-grow mx-10 my-10 overflow-hidden bg-coc-secondary-10L rounded shadow-lg">
        {children}
      </div>
      <Footer className="flex-shrink-0" />
    </motion.div>
  );
};

export default Layout;
