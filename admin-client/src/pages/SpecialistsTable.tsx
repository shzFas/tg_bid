import {
  Table, TableHead, TableRow, TableCell,
  TableBody, IconButton, Tooltip, Chip
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import CheckIcon from "@mui/icons-material/Check";

import {
  deleteSpecialist,
  approveSpecialist
} from "../api/specialists";

export default function SpecialistsTable({ specialists, refresh, onEdit }: any) {

  const handleDelete = async (id: number) => {
    await deleteSpecialist(id);
    refresh();
  };

  const handleApprove = async (id: number) => {
    await approveSpecialist(id);
    refresh();
  };

  return (
    <Table>
      <TableHead>
        <TableRow>
          <TableCell>ID</TableCell>
          <TableCell>Имя</TableCell>
          <TableCell>Телефон</TableCell>
          <TableCell>Специализации</TableCell>
          <TableCell>Одобрен?</TableCell>
          <TableCell>Действия</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {specialists.map((s: any) => (
          <TableRow key={s.id}>
            <TableCell>{s.id}</TableCell>
            <TableCell>{s.name}</TableCell>
            <TableCell>{s.phone}</TableCell>
            <TableCell>{s.specializations.join(", ")}</TableCell>
            <TableCell>
              <Chip
                label={s.is_approved ? "YES" : "NO"}
                color={s.is_approved ? "success" : "warning"}
              />
            </TableCell>

            <TableCell>
              {/* ОДОБРИТЬ */}
              {!s.is_approved && (
                <Tooltip title="Одобрить">
                  <IconButton onClick={() => handleApprove(s.id)}>
                    <CheckIcon color="success" />
                  </IconButton>
                </Tooltip>
              )}

              <Tooltip title="Редактировать">
                <IconButton>
                  <EditIcon onClick={() => onEdit(s)} />
                </IconButton>
              </Tooltip>

              <Tooltip title="Удалить">
                <IconButton onClick={() => handleDelete(s.id)}>
                  <DeleteIcon color="error" />
                </IconButton>
              </Tooltip>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
