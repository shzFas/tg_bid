import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import RequestsList from "../pages/RequestsList";
import RequestCreate from "../pages/RequestCreate";
import RequestDetail from "../pages/RequestDetail";
import RequestEdit from "../pages/RequestEdit";

export default function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/requests" />} />
        <Route path="/requests" element={<RequestsList />} />
        <Route path="/requests/create" element={<RequestCreate />} />
        <Route path="/requests/:id" element={<RequestDetail />} />
        <Route path="/requests/:id/edit" element={<RequestEdit />} />
      </Routes>
    </BrowserRouter>
  );
}
