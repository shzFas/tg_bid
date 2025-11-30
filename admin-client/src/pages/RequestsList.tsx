import { useEffect, useState } from "react";
import { Request } from "../types";
import { getRequests } from "../api/requests";
import {
  Table, TableBody, TableCell, TableContainer,
  TableHead, TableRow, Paper, Button, Box
} from "@mui/material";
import { Link } from "react-router-dom";

export default function RequestsList() {
  const [data, setData] = useState<Request[]>([]);

  useEffect(() => {
    getRequests().then(setData);
  }, []);

  return (
    <Box p={2}>
      <Button
        variant="contained"
        component={Link}
        to="/requests/create"
        sx={{ mb: 2 }}
      >
        ➕ Создать заявку
      </Button>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>ID</TableCell>
              <TableCell>Категория</TableCell>
              <TableCell>Имя</TableCell>
              <TableCell>Телефон</TableCell>
              <TableCell>Статус</TableCell>
              <TableCell>Действия</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {data.map((r) => (
              <TableRow key={r.id}>
                <TableCell>{r.id}</TableCell>
                <TableCell>{r.specialization}</TableCell>
                <TableCell>{r.name}</TableCell>
                <TableCell>{r.phone}</TableCell>
                <TableCell>{r.status}</TableCell>
                <TableCell>
                  <Button
                    component={Link}
                    to={`/requests/${r.id}`}
                    size="small"
                  >
                    Открыть
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}
