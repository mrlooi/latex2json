import json
from TexSoup import TexSoup
from typing import Dict, List, Optional
import re
import os

def count_characters(data):
    if isinstance(data, dict):
        return {k: count_characters(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [count_characters(item) for item in data]
    elif isinstance(data, str):
        return len(data)
    return 0

class LatexParser:
    def __init__(self):
        self.soup = None
        self.base_dir = None
        
    def parse_file(self, filepath: str) -> Dict:
        """
        Parse a LaTeX file and return a structured dictionary of its contents
        
        Args:
            filepath: Path to the LaTeX file
            
        Returns:
            Dictionary containing parsed LaTeX structure
        """
        try:
            self.base_dir = os.path.dirname(filepath)
            with open(filepath, 'r', encoding='utf-8') as file:
                tex_content = self._process_inputs(file.read())
            self.soup = TexSoup(tex_content)
            
            # Extract main components
            return {
                'title': self._extract_title(),
                'authors': self._extract_authors(),
                'abstract': self._extract_abstract(),
                'sections': self._extract_sections(),
                'bibliography': self._extract_bibliography()
            }
        except Exception as e:
            print(f"Error parsing LaTeX file: {str(e)}")
            return {}
    
    def _process_inputs(self, content: str) -> str:
        """Process \input commands and include referenced file contents"""
        input_pattern = r'\\input{([^}]+)}'
        
        def replace_input(match):
            input_file = match.group(1)
            if not input_file.endswith('.tex'):
                input_file += '.tex'
                
            input_path = os.path.join(self.base_dir, input_file)
            try:
                with open(input_path, 'r', encoding='utf-8') as f:
                    return self._process_inputs(f.read())  # Recursive processing for nested inputs
            except Exception as e:
                print(f"Warning: Could not process input file {input_path}: {str(e)}")
                return ''
                
        return re.sub(input_pattern, replace_input, content)
    
    def _extract_title(self) -> Optional[str]:
        """Extract document title"""
        try:
            title = self.soup.find('title')
            return str(title.string) if title else None
        except:
            return None
    
    def _extract_authors(self) -> List[str]:
        """Extract author names"""
        authors = []
        try:
            author_nodes = self.soup.find_all('author')
            for author in author_nodes:
                authors.append(str(author.string))
        except:
            pass
        return authors
    
    def _extract_abstract(self) -> Optional[str]:
        """Extract abstract content"""
        try:
            # 2. Try abstract command
            abstract = self.soup.find('abstract')
            if abstract and hasattr(abstract, 'contents'):
                return self._clean_text(' '.join(str(c) for c in abstract.contents))

            # 3. Try document class specific abstract
            abstract = self.soup.find('ABSTRACT')
            if abstract:
                return self._clean_text(str(abstract))

            print("Debug: Could not find abstract in document")
            print("Debug: Available environments:", [str(env.name) for env in self.soup.find_all() if hasattr(env, 'name')])
            return None

        except Exception as e:
            print(f"Debug: Error in abstract extraction: {str(e)}")
            return None
    
    def _extract_sections(self) -> List[Dict]:
        """Extract all sections and their content, including those from input files"""
        sections = []
        try:
            # Find all section-like commands (section, section*)
            all_sections = []
            for cmd in ['section', 'section*']:
                all_sections.extend(self.soup.find_all(cmd))
            
            # Sort sections based on their appearance in the document
            all_sections.sort(key=lambda x: str(self.soup).find(str(x)))
            
            for i, section in enumerate(all_sections):
                # Get the content between this section and the next one
                section_start = str(self.soup).find(str(section))
                if i < len(all_sections) - 1:
                    next_section = all_sections[i + 1]
                    section_end = str(self.soup).find(str(next_section))
                    content = str(self.soup)[section_start:section_end]
                else:
                    content = str(self.soup)[section_start:]
                
                section_dict = {
                    'title': self._clean_text(str(section.args[0])) if section.args else '',
                    'content': self._clean_text(content)
                }
                
                subsections = self._extract_subsections(section)
                if subsections:
                    section_dict['subsections'] = subsections
                sections.append(section_dict)
                
        except Exception as e:
            print(f"Debug: Error extracting sections: {str(e)}")
            pass
        return sections
    
    def _extract_subsections(self, section) -> List[Dict]:
        """Extract subsections from a section, including those from input files"""
        subsections = []
        try:
            # Find all subsection-like commands
            all_subsections = []
            for cmd in ['subsection', 'subsection*']:
                all_subsections.extend(section.find_all(cmd))
            
            # Sort subsections based on their appearance
            all_subsections.sort(key=lambda x: str(section).find(str(x)))
            
            for i, subsec in enumerate(all_subsections):
                # Get content between this subsection and the next one
                subsec_start = str(section).find(str(subsec))
                if i < len(all_subsections) - 1:
                    next_subsec = all_subsections[i + 1]
                    subsec_end = str(section).find(str(next_subsec))
                    content = str(section)[subsec_start:subsec_end]
                else:
                    content = str(section)[subsec_start:]
                
                subsection_dict = {
                    'title': self._clean_text(str(subsec.args[0])) if subsec.args else '',
                    'content': self._clean_text(content)
                }
                
                subsubsections = self._extract_subsubsections(subsec)
                if subsubsections:
                    subsection_dict['subsubsections'] = subsubsections
                subsections.append(subsection_dict)
                
        except Exception as e:
            print(f"Debug: Error extracting subsections: {str(e)}")
            pass
        return subsections
    
    def _extract_subsubsections(self, subsection) -> List[Dict]:
        """Extract subsubsections from a subsection"""
        subsubsections = []
        try:
            # Find all subsubsection-like commands
            all_subsubsections = []
            for cmd in ['subsubsection', 'subsubsection*']:
                all_subsubsections.extend(subsection.find_all(cmd))
            
            # Sort subsubsections based on their appearance
            all_subsubsections.sort(key=lambda x: str(subsection).find(str(x)))
            
            for i, subsubsec in enumerate(all_subsubsections):
                # Get content between this subsubsection and the next one
                subsubsec_start = str(subsection).find(str(subsubsec))
                if i < len(all_subsubsections) - 1:
                    next_subsubsec = all_subsubsections[i + 1]
                    subsubsec_end = str(subsection).find(str(next_subsubsec))
                    content = str(subsection)[subsubsec_start:subsubsec_end]
                else:
                    content = str(subsection)[subsubsec_start:]
                
                subsubsection_dict = {
                    'title': self._clean_text(str(subsubsec.args[0])) if subsubsec.args else '',
                    'content': self._clean_text(content)
                }
                subsubsections.append(subsubsection_dict)
                
        except Exception as e:
            print(f"Debug: Error extracting subsubsections: {str(e)}")
            pass
        return subsubsections
    
    def _extract_bibliography(self) -> Dict[str, str]:
        """Extract bibliography entries"""
        bibliography = []
        try:
            bib_items = self.soup.find_all('bibitem')
            for item in bib_items:
                # Extract citation key and content
                bibliography.append(item.string)
        except:
            pass
        return bibliography
    
    def _clean_text(self, text: str) -> str:
        return text

def main():
    # Example usage
    parser = LatexParser()
    
    try:
        with open('papers/arXiv-1706.03762v7/ms.tex', 'r', encoding='utf-8') as file:
            print("Debug: Successfully opened file")
            content = file.read()
            print(f"Debug: File length: {len(content)} characters")
            print("Debug: First 200 characters of file:", content[:200])
    except Exception as e:
        print(f"Debug: Error reading file: {str(e)}")
        return
    
    result = parser.parse_file('papers/arXiv-1706.03762v7/ms.tex')
    
    # # Debug information
    # print("\nDocument structure:")
    # if parser.soup:
    #     try:
    #         all_commands = []
    #         soup_contents = parser.soup.find_all()
    #         if soup_contents:  # Add check for None
    #             for cmd in soup_contents:
    #                 if cmd and hasattr(cmd, 'name') and cmd.name:
    #                     all_commands.append(str(cmd.name))
    #             print("Available commands:", all_commands[:20], "..." if len(all_commands) > 20 else "")
    #         else:
    #             print("Debug: No commands found in soup")
    #     except Exception as e:
    #         print(f"Debug: Error getting commands: {str(e)}")
    #         print(f"Debug: Soup content type: {type(parser.soup)}")
    #         print(f"Debug: Raw soup content: {parser.soup}")
    # else:
    #     print("Debug: No soup object created")
    
    # # Print parsed results
    # print("\nTitle:", result['title'])
    # print("\nAuthors:", ', '.join(result['authors']))
    # print("\nAbstract:", result['abstract'])
    
    # print("\nSections:")
    # for section in result['sections']:
    #     print(f"\n- {section['title']}")

    return result, parser

if __name__ == '__main__':
    res, parser = main()

    # store res in data/folder
    with open('data/res.json', 'w') as f:
        json.dump(res, f)
    