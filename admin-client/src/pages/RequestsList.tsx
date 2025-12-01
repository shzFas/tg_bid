import { useEffect, useState } from "react";
import { Request } from "../types";
import { getRequests } from "../api/requests";
import {
  Table, TableBody, TableCell, TableContainer,
  TableHead, TableRow, Paper, Button, Box, Typography
} from "@mui/material";

import { Link } from "react-router-dom";
import { useSnackbar } from "../components/SnackbarProvider";

export default function RequestsList() {
  const [data, setData] = useState<Request[]>([]);
  const { showMessage } = useSnackbar();

  const refresh = async () => {
    try {
      const result = await getRequests();
      if (Array.isArray(result)) {
        setData(result);
      } else {
        setData([]);
      }
    } catch (err: any) {
      showMessage(err.message, "error");
    }
  };

  useEffect(() => {
    refresh();
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

      {/* Если данных нет */}
      {data.length === 0 && (
        <Typography sx={{ mt: 2 }}>Заявок пока нет.</Typography>
      )}

      {data.length > 0 && (
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
      )}
    </Box>
  );
}
