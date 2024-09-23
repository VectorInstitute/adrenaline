import React, { useState, useCallback, KeyboardEvent } from 'react'
import {
  InputGroup,
  InputLeftElement,
  Input,
  Button,
  Flex,
  Icon,
  useColorModeValue,
} from '@chakra-ui/react'
import { FaSearch } from 'react-icons/fa'

interface SearchBarProps {
  onSearch: (query: string) => void
  isLoading: boolean
}

const SearchBar: React.FC<SearchBarProps> = ({ onSearch, isLoading }) => {
  const [query, setQuery] = useState<string>('')

  const handleQueryChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setQuery(e.target.value)
  }, [])

  const handleSearch = useCallback(() => {
    onSearch(query)
  }, [query, onSearch])

  const handleKeyPress = useCallback((e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSearch()
    }
  }, [handleSearch])

  const borderColor = useColorModeValue('teal.200', 'teal.700')
  const primaryColor = useColorModeValue('teal.600', 'teal.300')

  return (
    <Flex direction={{ base: 'column', md: 'row' }} spacing={4} align="center">
      <InputGroup flex={1} mb={{ base: 4, md: 0 }}>
        <InputLeftElement pointerEvents="none">
          <Icon as={FaSearch} color="teal.400" />
        </InputLeftElement>
        <Input
          value={query}
          onChange={handleQueryChange}
          onKeyPress={handleKeyPress}
          placeholder="Enter query or patient ID..."
          borderColor={borderColor}
          _hover={{ borderColor: primaryColor }}
          _focus={{ borderColor: primaryColor, boxShadow: `0 0 0 1px ${primaryColor}` }}
          fontSize="lg"
          height="50px"
        />
      </InputGroup>
      <Button
        colorScheme="teal"
        onClick={handleSearch}
        isLoading={isLoading}
        loadingText="Searching..."
        size="lg"
        width={{ base: 'full', md: 'auto' }}
        height="50px"
        fontSize="lg"
        fontWeight="semibold"
        ml={{ md: 4 }}
        mt={{ base: 4, md: 0 }}
        _hover={{ bg: 'teal.500' }}
        _active={{ bg: 'teal.600' }}
      >
        Search
      </Button>
    </Flex>
  )
}

export default SearchBar
