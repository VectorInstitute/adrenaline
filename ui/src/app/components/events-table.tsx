import React, { useMemo } from 'react'
import { useTable, useSortBy, useFlexLayout } from 'react-table'
import {
  Table, Thead, Tbody, Tr, Th, Td, chakra, Badge, Box, useColorModeValue,
  Text, Tooltip, VStack
} from '@chakra-ui/react'
import { TriangleDownIcon, TriangleUpIcon } from '@chakra-ui/icons'
import { Event } from '../types/patient'

interface EventsTableProps {
  events: Event[]
}

const EventsTable: React.FC<EventsTableProps> = ({ events }) => {
  const data = useMemo(() => events, [events])
  const columns = useMemo(
    () => [
      {
        Header: 'Timestamp',
        accessor: 'timestamp',
        width: 150,
        Cell: ({ value }: { value: string }) => {
          const date = new Date(value)
          return (
            <VStack align="start" spacing={0}>
              <Text fontWeight="bold" fontSize="xs">{date.toLocaleDateString()}</Text>
              <Text fontSize="xs" color="gray.500">{date.toLocaleTimeString()}</Text>
            </VStack>
          )
        },
      },
      {
        Header: 'Event Type',
        accessor: (row: Event) => row.code.split('//')[0],
        width: 120,
        Cell: ({ value }: { value: string }) => (
          <Badge colorScheme={getEventColor(value)} fontSize="2xs" px={1} py={0.5} borderRadius="full">
            {value}
          </Badge>
        ),
      },
      {
        Header: 'Details',
        accessor: (row: Event) => row.code.split('//').slice(1).join(', '),
        width: 250,
        Cell: ({ value }: { value: string }) => (
          <Tooltip label={value} placement="top-start" hasArrow>
            <Text isTruncated maxWidth="230px" fontSize="xs">{value}</Text>
          </Tooltip>
        ),
      },
      {
        Header: 'Value',
        accessor: (row: Event) => row.numeric_value || row.text_value || 'N/A',
        width: 100,
        Cell: ({ value }: { value: string | number }) => (
          <Text fontSize="xs">{value}</Text>
        ),
      },
    ],
    []
  )

  const {
    getTableProps,
    getTableBodyProps,
    headerGroups,
    rows,
    prepareRow,
  } = useTable(
    { columns, data },
    useSortBy,
    useFlexLayout
  )

  const bgColor = useColorModeValue('white', 'gray.800')
  const borderColor = useColorModeValue('gray.200', 'gray.600')
  const hoverBgColor = useColorModeValue('gray.50', 'gray.700')

  return (
    <Box
      bg={bgColor}
      borderWidth={1}
      borderColor={borderColor}
      borderRadius="md"
      boxShadow="sm"
    >
      <Table {...getTableProps()} size="sm">
        <Thead position="sticky" top={0} bg={bgColor} zIndex={1} boxShadow="sm">
          {headerGroups.map((headerGroup) => (
            <Tr {...headerGroup.getHeaderGroupProps()}>
              {headerGroup.headers.map((column) => (
                <Th
                  {...column.getHeaderProps(column.getSortByToggleProps())}
                  isNumeric={column.isNumeric}
                  px={2}
                  py={2}
                  borderBottom="2px"
                  borderColor={borderColor}
                  fontWeight="bold"
                  textTransform="uppercase"
                  letterSpacing="wider"
                  fontSize="2xs"
                  cursor="pointer"
                  _hover={{ bg: hoverBgColor }}
                >
                  <chakra.span display="flex" alignItems="center">
                    {column.render('Header')}
                    <chakra.span ml={1}>
                      {column.isSorted ? (
                        column.isSortedDesc ? (
                          <TriangleDownIcon aria-label="sorted descending" boxSize={2} />
                        ) : (
                          <TriangleUpIcon aria-label="sorted ascending" boxSize={2} />
                        )
                      ) : null}
                    </chakra.span>
                  </chakra.span>
                </Th>
              ))}
            </Tr>
          ))}
        </Thead>
        <Tbody {...getTableBodyProps()}>
          {rows.map((row) => {
            prepareRow(row)
            return (
              <Tr
                {...row.getRowProps()}
                _hover={{ bg: hoverBgColor }}
                transition="background-color 0.2s"
              >
                {row.cells.map((cell) => (
                  <Td
                    {...cell.getCellProps()}
                    isNumeric={cell.column.isNumeric}
                    px={2}
                    py={2}
                    borderBottom="1px"
                    borderColor={borderColor}
                  >
                    {cell.render('Cell')}
                  </Td>
                ))}
              </Tr>
            )
          })}
        </Tbody>
      </Table>
    </Box>
  )
}

const getEventColor = (eventType: string): string => {
  const colorMap: Record<string, string> = {
    LAB: 'blue',
    MEDICATION: 'purple',
    DIAGNOSIS: 'red',
    TRANSFER: 'green',
    PROCEDURE: 'orange',
    TRANSFER_TO: 'teal',
    TRANSFER_FROM: 'teal',
    HOSPITAL_ADMISSION: 'pink',
    HOSPITAL_DISCHARGE: 'pink',
  }
  return colorMap[eventType] || 'gray'
}

export default EventsTable
