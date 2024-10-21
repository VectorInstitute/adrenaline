import React, { useState, useCallback } from 'react';
import TextareaAutosize from 'react-textarea-autosize';
import { Flex, Button, Text, Switch, useColorModeValue, Box } from '@chakra-ui/react';
import { ArrowUpIcon } from '@chakra-ui/icons';

interface SearchBoxProps {
  onSearch: (query: string, isPatientMode: boolean) => void;
  isLoading: boolean;
  isPatientPage?: boolean;
  isCohortPage?: boolean;
}

const SearchBox: React.FC<SearchBoxProps> = ({
  onSearch,
  isLoading,
  isPatientPage = false,
  isCohortPage = false
}) => {
  const [query, setQuery] = useState<string>('');
  const [isPatientMode, setIsPatientMode] = useState<boolean>(false);

  const handleQueryChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setQuery(e.target.value);
  }, []);

  const handleSearch = useCallback(() => {
    if (query.trim()) {
      onSearch(query.trim(), isPatientMode);
    }
  }, [query, onSearch, isPatientMode]);

  const handleKeyPress = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSearch();
    }
  }, [handleSearch]);

  const toggleMode = useCallback(() => {
    setIsPatientMode(prev => !prev);
  }, []);

  const bgColor = useColorModeValue('white', 'gray.800');
  const buttonBgColor = useColorModeValue('#1f5280', '#3a7ab3');
  const modeTextColor = useColorModeValue('gray.600', 'gray.400');

  const getPlaceholder = () => {
    if (isPatientPage) return "Ask a question about this patient...";
    if (isCohortPage) return "Enter a query to search across all patients...";
    return isPatientMode ? "Enter patient ID" : "Ask a question about the cohort...";
  };

  return (
    <Box w="100%" maxW="600px" my={4}>
      <Flex
        direction="column"
        border="2px solid"
        borderColor="gray.200"
        borderRadius="md"
        overflow="hidden"
        position="relative"
      >
        <TextareaAutosize
          value={query}
          onChange={handleQueryChange}
          onKeyPress={handleKeyPress}
          placeholder={getPlaceholder()}
          minRows={3}
          maxRows={10}
          style={{
            width: '100%',
            resize: 'none',
            border: 'none',
            outline: 'none',
            padding: '12px 16px',
            paddingRight: '100px',
            backgroundColor: bgColor,
            color: 'inherit',
            fontSize: '16px',
            lineHeight: '1.5',
            fontFamily: "'Roboto Slab', serif",
            maxRows: '300px',
            overflowY: 'auto',
          }}
        />
        <Flex
          position="absolute"
          right={2}
          bottom={2}
          align="center"
          flexDirection={{ base: 'column', sm: 'row' }}
        >
          {!isPatientPage && !isCohortPage && (
            <Flex align="center" mb={{ base: 2, sm: 0 }} mr={{ base: 0, sm: 2 }}>
              <Text fontSize="xs" fontWeight="medium" color={modeTextColor} mr={2}>
                {isPatientMode ? "Patient" : "Cohort"}
              </Text>
              <Switch
                size="sm"
                isChecked={isPatientMode}
                onChange={toggleMode}
              />
            </Flex>
          )}
          <Button
            size="sm"
            colorScheme="blue"
            isLoading={isLoading}
            onClick={handleSearch}
            bg={buttonBgColor}
            p={2}
            minW="auto"
          >
            <ArrowUpIcon />
          </Button>
        </Flex>
      </Flex>
    </Box>
  );
};

export default SearchBox;
