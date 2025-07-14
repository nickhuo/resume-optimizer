"""
LaTeX compilation utility using latexmk.
"""
import subprocess
import logging
from pathlib import Path
from typing import Optional, List
import shutil
import tempfile

logger = logging.getLogger(__name__)


class LatexCompiler:
    """Utility to compile LaTeX files to PDF using latexmk."""
    
    def __init__(self):
        """Initialize the LaTeX compiler."""
        # Check if latexmk is available
        if not self._check_latexmk():
            raise RuntimeError("latexmk not found. Please install TeX distribution (e.g., MacTeX, TeX Live).")
    
    def compile(
        self, 
        tex_file: Path,
        output_dir: Optional[Path] = None,
        clean_aux: bool = True,
        timeout: int = 60
    ) -> Path:
        """
        Compile LaTeX file to PDF.
        
        Args:
            tex_file: Path to the .tex file
            output_dir: Directory for output files. If None, uses tex file directory
            clean_aux: Whether to clean auxiliary files after compilation
            timeout: Compilation timeout in seconds
            
        Returns:
            Path to the generated PDF file
            
        Raises:
            RuntimeError: If compilation fails
        """
        if not tex_file.exists():
            raise FileNotFoundError(f"TeX file not found: {tex_file}")
        
        # Determine output directory
        if output_dir is None:
            output_dir = tex_file.parent
        else:
            output_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy necessary files to a temporary directory for compilation
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Copy the tex file
            temp_tex_file = temp_path / tex_file.name
            shutil.copy(tex_file, temp_tex_file)
            
            # Copy the cls file if it exists
            # Try multiple possible locations for resume.cls
            possible_cls_locations = [
                tex_file.parent / "resume.cls",
                tex_file.parent.parent / "templates" / "resume.cls",
                tex_file.parent.parent / "resume_builder" / "templates" / "resume.cls",
                tex_file.parent.parent / "resume_builder" / "resume.cls",
                Path(__file__).parent.parent / "templates" / "resume.cls",
                Path(__file__).parent.parent / "resume.cls",
            ]
            
            cls_file = None
            for loc in possible_cls_locations:
                if loc.exists():
                    cls_file = loc
                    break
            
            if cls_file:
                shutil.copy(cls_file, temp_path / "resume.cls")
                logger.debug(f"Copied resume.cls from {cls_file}")
            else:
                logger.warning("resume.cls not found, compilation may fail")
            
            # Prepare latexmk command
            cmd = [
                "latexmk",
                "-pdf",                    # Generate PDF
                "-xelatex",               # Use XeLaTeX engine
                "-interaction=batchmode",  # Non-interactive mode
                "-quiet",                 # Reduce output
                f"-output-directory={temp_path}",
                str(temp_tex_file)
            ]
            
            logger.info(f"Compiling LaTeX file: {tex_file.name}")
            logger.debug(f"Command: {' '.join(cmd)}")
            
            try:
                # Run compilation
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=temp_path  # Set working directory
                )
                
                if result.returncode != 0:
                    # Try to get meaningful error from log file
                    log_file = temp_path / f"{tex_file.stem}.log"
                    error_msg = self._extract_error_from_log(log_file) if log_file.exists() else result.stderr
                    raise RuntimeError(f"LaTeX compilation failed: {error_msg}")
                
                # Check if PDF was generated
                pdf_file = temp_path / f"{tex_file.stem}.pdf"
                if not pdf_file.exists():
                    raise RuntimeError("PDF file was not generated")
                
                # Copy PDF to output directory
                output_pdf = output_dir / pdf_file.name
                shutil.copy(pdf_file, output_pdf)
                
                logger.info(f"Successfully compiled PDF: {output_pdf}")
                
                # Clean auxiliary files if requested
                if clean_aux:
                    self._clean_aux_files(output_dir, tex_file.stem)
                
                return output_pdf
                
            except subprocess.TimeoutExpired:
                raise RuntimeError(f"LaTeX compilation timed out after {timeout} seconds")
            except Exception as e:
                logger.error(f"Compilation error: {str(e)}")
                raise
    
    def _check_latexmk(self) -> bool:
        """Check if latexmk is available in PATH."""
        try:
            result = subprocess.run(
                ["latexmk", "-version"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def _extract_error_from_log(self, log_file: Path) -> str:
        """Extract error messages from LaTeX log file."""
        try:
            content = log_file.read_text(encoding='utf-8', errors='ignore')
            
            # Look for error patterns
            error_lines = []
            lines = content.split('\n')
            
            for i, line in enumerate(lines):
                if line.startswith('!') or 'Error:' in line:
                    # Get context around error
                    start = max(0, i - 2)
                    end = min(len(lines), i + 3)
                    error_lines.extend(lines[start:end])
            
            if error_lines:
                return '\n'.join(error_lines)
            else:
                return "Unknown compilation error (check log file)"
                
        except Exception:
            return "Failed to read log file"
    
    def _clean_aux_files(self, directory: Path, basename: str):
        """Clean auxiliary LaTeX files."""
        aux_extensions = [
            '.aux', '.log', '.out', '.toc', '.lof', '.lot',
            '.bbl', '.blg', '.fls', '.fdb_latexmk', '.synctex.gz',
            '.nav', '.snm', '.vrb'
        ]
        
        for ext in aux_extensions:
            aux_file = directory / f"{basename}{ext}"
            if aux_file.exists():
                try:
                    aux_file.unlink()
                    logger.debug(f"Removed auxiliary file: {aux_file}")
                except Exception as e:
                    logger.warning(f"Failed to remove {aux_file}: {e}")
