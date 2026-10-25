import os
import pathlib
import struct
import math
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import configparser
from concurrent.futures import ThreadPoolExecutor, as_completed

BLOCK_SIZE = 2048
COPY_BUFFER_SIZE = 4 * 1024 * 1024

class IMGArchiveCreatorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("GTA San Andreas IMG Archive Creator")
        self.root.geometry("900x700")
        self.root.minsize(700, 500)
        
        self.folder_queue = []
        self.game_folder = None
        self.worker_count = max(1, os.cpu_count() or 1)
        self.setup_gui()
        
    def setup_gui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(5, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="GTA San Andreas IMG Archive Creator", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Game folder selection section
        game_frame = ttk.LabelFrame(main_frame, text="Game Folder", padding="10")
        game_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        game_frame.columnconfigure(1, weight=1)
        
        ttk.Label(game_frame, text="Game Root Folder:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.game_folder_var = tk.StringVar()
        self.game_folder_entry = ttk.Entry(game_frame, textvariable=self.game_folder_var, state='readonly')
        self.game_folder_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        
        ttk.Button(game_frame, text="Select Game Folder", command=self.select_game_folder).grid(row=0, column=2)
        
        # INI file section
        ini_frame = ttk.LabelFrame(main_frame, text="Configuration", padding="10")
        ini_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        ini_frame.columnconfigure(0, weight=1)
        
        ini_button_frame = ttk.Frame(ini_frame)
        ini_button_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        ttk.Button(ini_button_frame, text="Save Configuration", command=self.save_ini).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(ini_button_frame, text="Load Configuration", command=self.load_ini).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(ini_button_frame, text="New Configuration", command=self.new_configuration).pack(side=tk.LEFT)
        
        # Add folder section
        add_frame = ttk.LabelFrame(main_frame, text="Add Folders", padding="10")
        add_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        add_frame.columnconfigure(1, weight=1)
        
        # Folder path entry
        ttk.Label(add_frame, text="Folder Path (relative to game folder):").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.folder_path_var = tk.StringVar()
        self.folder_entry = ttk.Entry(add_frame, textvariable=self.folder_path_var)
        self.folder_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        
        ttk.Button(add_frame, text="Browse", command=self.browse_folder).grid(row=0, column=2)
        
        # Add button
        ttk.Button(add_frame, text="Add to Queue", command=self.add_folder).grid(row=1, column=1, pady=(10, 0))
        
        # Build options section
        options_frame = ttk.LabelFrame(main_frame, text="Build Options", padding="10")
        options_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.delete_source_var = tk.BooleanVar()
        self.delete_source_check = ttk.Checkbutton(
            options_frame, 
            text="Build for Public Release (Delete source folders after conversion)", 
            variable=self.delete_source_var
        )
        self.delete_source_check.grid(row=0, column=0, sticky=tk.W)

        ttk.Label(
            options_frame,
            text=f"Parallel archive workers: {self.worker_count} (all logical CPUs)"
        ).grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        
        # Queue management section
        queue_frame = ttk.LabelFrame(main_frame, text="Conversion Queue", padding="10")
        queue_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        queue_frame.columnconfigure(0, weight=1)
        queue_frame.rowconfigure(0, weight=1)
        
        # Treeview for queue
        columns = ("Folder", "Output", "Files")
        self.tree = ttk.Treeview(queue_frame, columns=columns, show="headings", height=8)
        
        # Configure columns
        self.tree.heading("Folder", text="Relative Path")
        self.tree.heading("Output", text="Output Path")
        self.tree.heading("Files", text="File Count")
        
        self.tree.column("Folder", width=300)
        self.tree.column("Output", width=300)
        self.tree.column("Files", width=80)
        
        # Scrollbar for treeview
        scrollbar = ttk.Scrollbar(queue_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Queue control buttons
        button_frame = ttk.Frame(queue_frame)
        button_frame.grid(row=1, column=0, columnspan=2, pady=(10, 0))
        
        ttk.Button(button_frame, text="Remove Selected", command=self.remove_selected).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Clear All", command=self.clear_queue).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Convert All", command=self.start_conversion).pack(side=tk.LEFT, padx=(10, 0))
        ttk.Button(button_frame, text="Delete Sources Only", command=self.start_delete_sources_only).pack(side=tk.LEFT, padx=(10, 0))
        
        # Progress section
        progress_frame = ttk.LabelFrame(main_frame, text="Progress", padding="10")
        progress_frame.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        progress_frame.columnconfigure(0, weight=1)
        
        self.progress_var = tk.StringVar(value="Ready - Please select game folder first")
        self.progress_label = ttk.Label(progress_frame, textvariable=self.progress_var)
        self.progress_label.grid(row=0, column=0, sticky=tk.W)
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress_bar.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        
        # Log section
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="10")
        log_frame.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, width=70)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure main frame row weights
        main_frame.rowconfigure(7, weight=1)
        
    def select_game_folder(self):
        """Select the game root folder"""
        folder = filedialog.askdirectory(title="Select GTA San Andreas Root Folder")
        if folder:
            self.game_folder = pathlib.Path(folder)
            self.game_folder_var.set(str(self.game_folder))
            self.progress_var.set("Game folder selected - Ready to add folders")
            self.log_message(f"✓ Game folder set: {self.game_folder}")
            
    def get_relative_path(self, full_path):
        """Convert absolute path to relative path from game folder"""
        if not self.game_folder:
            return str(full_path)
        
        try:
            path = pathlib.Path(full_path)
            relative = path.relative_to(self.game_folder)
            return str(relative).replace('\\', '/')  # Use forward slashes for consistency
        except ValueError:
            # Path is not relative to game folder
            return str(full_path)
    
    def get_absolute_path(self, relative_path):
        """Convert relative path to absolute path using game folder"""
        if not self.game_folder:
            return pathlib.Path(relative_path)
        
        # Clean up the relative path
        relative_path = relative_path.replace('/', '\\')  # Convert to Windows path separators
        if relative_path.startswith('\\'):
            relative_path = relative_path[1:]  # Remove leading backslash
            
        return self.game_folder / relative_path
        
    def save_ini(self):
        """Save current folder queue to INI file"""
        if not self.folder_queue:
            messagebox.showwarning("Warning", "No folders in queue to save")
            return
            
        if not self.game_folder:
            messagebox.showerror("Error", "Please select game folder first")
            return
            
        filename = filedialog.asksaveasfilename(
            title="Save Configuration",
            defaultextension=".ini",
            filetypes=[("INI files", "*.ini"), ("All files", "*.*")]
        )
        
        if not filename:
            return
            
        try:
            config = configparser.ConfigParser()
            
            # Add metadata section
            config['Metadata'] = {
                'version': '1.0',
                'created_by': 'GTA SA IMG Archive Creator',
                'folder_count': str(len(self.folder_queue)),
                'game_folder': str(self.game_folder),
                'delete_source_folders': str(self.delete_source_var.get())
            }
            
            # Add each folder as a section
            for i, item in enumerate(self.folder_queue):
                section_name = f"Folder_{i+1}"
                config[section_name] = {
                    'source_path': item['relative_source'],
                    'output_path': item['relative_output'],
                    'file_count': str(item['file_count'])
                }
            
            with open(filename, 'w') as config_file:
                config.write(config_file)
                
            self.log_message(f"✓ Configuration saved: {filename}")
            messagebox.showinfo("Success", f"Configuration saved successfully!\n{len(self.folder_queue)} folders saved to {pathlib.Path(filename).name}")
            
        except Exception as e:
            self.log_message(f"Error saving configuration: {e}")
            messagebox.showerror("Error", f"Failed to save configuration:\n{e}")
    
    def load_ini(self):
        """Load folder queue from INI file"""
        filename = filedialog.askopenfilename(
            title="Load Configuration",
            filetypes=[("INI files", "*.ini"), ("All files", "*.*")]
        )
        
        if not filename:
            return
            
        try:
            config = configparser.ConfigParser()
            config.read(filename)
            
            # Check if this is a valid configuration file
            if 'Metadata' not in config:
                messagebox.showerror("Error", "Invalid configuration file format")
                return
            
            # Set game folder from INI if not already set
            if 'game_folder' in config['Metadata']:
                ini_game_folder = config['Metadata']['game_folder']
                if not self.game_folder:
                    # Ask user if they want to use the game folder from INI
                    if messagebox.askyesno("Game Folder", f"Use game folder from INI file?\n{ini_game_folder}"):
                        if pathlib.Path(ini_game_folder).exists():
                            self.game_folder = pathlib.Path(ini_game_folder)
                            self.game_folder_var.set(str(self.game_folder))
                            self.log_message(f"✓ Game folder loaded from INI: {self.game_folder}")
                        else:
                            messagebox.showerror("Error", f"Game folder from INI does not exist:\n{ini_game_folder}")
                            return
            
            # Load build options
            if 'delete_source_folders' in config['Metadata']:
                delete_source = config['Metadata'].getboolean('delete_source_folders', False)
                self.delete_source_var.set(delete_source)
                if delete_source:
                    self.log_message("✓ Build for Public Release option loaded: Enabled")
                else:
                    self.log_message("✓ Build for Public Release option loaded: Disabled")
            
            if not self.game_folder:
                messagebox.showerror("Error", "Please select game folder first")
                return
            
            # Clear current queue
            if self.folder_queue:
                if not messagebox.askyesno("Confirm", "This will replace the current queue. Continue?"):
                    return
                self.clear_queue()
            
            # Get folder sections and count
            folder_sections = [section for section in config.sections() if section.startswith('Folder_')]
            folder_sections.sort(key=lambda x: int(x.split('_')[1]))  # Sort by number
            
            total_folders = len(folder_sections)
            if total_folders == 0:
                messagebox.showwarning("Warning", "No folders found in configuration file")
                return
            
            # Setup progress bar for loading
            self.progress_bar.configure(maximum=total_folders, value=0)
            self.progress_var.set("Loading configuration...")
            
            loaded_count = 0
            skipped_count = 0
            
            for i, section_name in enumerate(folder_sections):
                # Update progress
                self.progress_var.set(f"Loading {i+1}/{total_folders}: {section_name}")
                self.progress_bar.configure(value=i+1)
                self.root.update_idletasks()  # Update GUI
                
                try:
                    relative_source = config[section_name]['source_path']
                    relative_output = config[section_name]['output_path']
                    # Use stored file count instead of recounting
                    stored_file_count = int(config[section_name].get('file_count', 0))
                    
                    # Convert to absolute paths
                    absolute_source = self.get_absolute_path(relative_source)
                    absolute_output = self.get_absolute_path(relative_output)
                    
                    # Only check if source folder exists (don't count files)
                    if not absolute_source.exists() or not absolute_source.is_dir():
                        self.log_message(f"⚠ Skipped (folder not found): {relative_source}")
                        skipped_count += 1
                        continue
                    
                    # Add to queue with stored file count
                    self.folder_queue.append({
                        'folder': absolute_source,
                        'output': absolute_output,
                        'relative_source': relative_source,
                        'relative_output': relative_output,
                        'file_count': stored_file_count  # Use stored count
                    })
                    
                    # Add to treeview with stored file count
                    self.tree.insert("", "end", values=(relative_source, relative_output, stored_file_count))
                    
                    loaded_count += 1
                    
                except Exception as e:
                    self.log_message(f"⚠ Error loading {section_name}: {e}")
                    skipped_count += 1
            
            # Reset progress bar
            self.progress_bar.configure(value=0)
            self.progress_var.set("Configuration loaded successfully!")
            
            self.log_message(f"✓ Configuration loaded: {loaded_count} folders loaded, {skipped_count} skipped")
            
            if loaded_count > 0:
                messagebox.showinfo("Success", f"Configuration loaded successfully!\n{loaded_count} folders loaded\n{skipped_count} folders skipped")
            else:
                messagebox.showwarning("Warning", "No valid folders were loaded from the configuration file")
                
        except Exception as e:
            self.progress_bar.configure(value=0)
            self.progress_var.set("Error loading configuration")
            self.log_message(f"Error loading configuration: {e}")
            messagebox.showerror("Error", f"Failed to load configuration:\n{e}")
    
    def new_configuration(self):
        """Start a new configuration (clear current queue)"""
        if not self.folder_queue:
            return
            
        if messagebox.askyesno("Confirm", "Clear all folders from queue to start a new configuration?"):
            self.clear_queue()
            self.log_message("Started new configuration")
        
    def log_message(self, message):
        """Add message to log with timestamp"""
        if threading.current_thread() is not threading.main_thread():
            self.root.after(0, self.log_message, message)
            return
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def update_progress(self, text=None, value=None, maximum=None):
        """Safely update progress widgets from any thread."""
        if threading.current_thread() is not threading.main_thread():
            self.root.after(0, self.update_progress, text, value, maximum)
            return
        if text is not None:
            self.progress_var.set(text)
        if maximum is not None:
            self.progress_bar.configure(maximum=maximum)
        if value is not None:
            self.progress_bar.configure(value=value)
        
    def browse_folder(self):
        """Browse for folder to add"""
        if not self.game_folder:
            messagebox.showerror("Error", "Please select game folder first")
            return
            
        folder = filedialog.askdirectory(
            title="Select Folder to Convert",
            initialdir=str(self.game_folder)
        )
        if folder:
            relative_path = self.get_relative_path(folder)
            self.folder_path_var.set(relative_path)
            
    def add_folder(self):
        """Add folder to conversion queue"""
        if not self.game_folder:
            messagebox.showerror("Error", "Please select game folder first")
            return
            
        relative_path = self.folder_path_var.get().strip()
        
        if not relative_path:
            messagebox.showerror("Error", "Please enter a folder path")
            return
        
        # Convert to absolute path
        absolute_path = self.get_absolute_path(relative_path)
        
        if not absolute_path.exists() or not absolute_path.is_dir():
            messagebox.showerror("Error", f"Folder does not exist: {absolute_path}")
            return
            
        # Auto-generate output path
        relative_output = relative_path + '.img'
        absolute_output = self.get_absolute_path(relative_output)
        
        # Show progress while counting files
        self.progress_var.set("Counting files...")
        self.root.update_idletasks()
        
        # Check if folder has files
        files = [f for f in absolute_path.iterdir() if f.is_file()]
        if not files:
            self.progress_var.set("Ready to add folders")
            messagebox.showwarning("Warning", f"Folder is empty: {relative_path}")
            return
            
        # Add to queue
        self.folder_queue.append({
            'folder': absolute_path,
            'output': absolute_output,
            'relative_source': relative_path,
            'relative_output': relative_output,
            'file_count': len(files)
        })
        
        # Add to treeview
        self.tree.insert("", "end", values=(relative_path, relative_output, len(files)))
        
        # Clear entry
        self.folder_path_var.set("")
        
        self.progress_var.set("Ready to add folders")
        self.log_message(f"✓ Added: {relative_path} ({len(files)} files)")
        
    def remove_selected(self):
        """Remove selected item from queue"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select an item to remove")
            return
            
        for item in selected:
            index = self.tree.index(item)
            removed = self.folder_queue.pop(index)
            self.tree.delete(item)
            self.log_message(f"Removed: {removed['relative_source']}")
            
    def clear_queue(self):
        """Clear all items from queue"""
        if not self.folder_queue:
            return
            
        self.folder_queue.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.log_message("Queue cleared")
            
    def create_img_from_folder(self, folder_path, output_img_path):
        """Create one IMG archive using buffered, memory-efficient I/O."""
        folder = pathlib.Path(folder_path)
        output_img = pathlib.Path(output_img_path)
        temp_img = output_img.with_name(
            f".{output_img.name}.{os.getpid()}.{threading.get_ident()}.tmp"
        )
        
        try:
            files = sorted(
                (f for f in folder.iterdir() if f.is_file()),
                key=lambda path: path.name.lower()
            )

            header_size = 8 + (len(files) * 32)
            header_blocks = math.ceil(header_size / BLOCK_SIZE)
            
            entries = []
            current_offset = header_blocks
            
            for file_path in files:
                file_size = file_path.stat().st_size
                size_blocks = math.ceil(file_size / BLOCK_SIZE)
                if size_blocks > 0xFFFF:
                    raise ValueError(
                        f"{file_path.name} is too large for IMG VER2 "
                        f"({file_size / (1024 * 1024):.1f} MB; maximum is about 128 MB)"
                    )
                
                entries.append({
                    'name': file_path.name,
                    'offset': current_offset,
                    'size_blocks': size_blocks,
                    'file_path': file_path
                })
                current_offset += size_blocks
            
            output_img.parent.mkdir(parents=True, exist_ok=True)

            # Pre-sizing makes all alignment gaps zero without issuing a
            # separate padding write for every source file.
            with open(temp_img, 'w+b', buffering=COPY_BUFFER_SIZE) as img_file:
                img_file.truncate(current_offset * BLOCK_SIZE)
                img_file.seek(0)
                img_file.write(b'VER2')
                img_file.write(struct.pack('<I', len(entries)))
                
                for entry in entries:
                    name_bytes = entry['name'].encode('ascii', errors='replace')
                    name_bytes = name_bytes[:24]
                    name_padded = name_bytes + b'\x00' * (24 - len(name_bytes))
                    img_file.write(struct.pack(
                        '<IHH24s',
                        entry['offset'],
                        entry['size_blocks'],
                        0,
                        name_padded
                    ))
                
                for entry in entries:
                    img_file.seek(entry['offset'] * BLOCK_SIZE)
                    with open(
                        entry['file_path'],
                        'rb',
                        buffering=COPY_BUFFER_SIZE
                    ) as src_file:
                        shutil.copyfileobj(
                            src_file,
                            img_file,
                            length=COPY_BUFFER_SIZE
                        )

                img_file.flush()

            # A failed build never leaves a half-written archive at the final path.
            os.replace(temp_img, output_img)
            
            return (
                True,
                len(entries),
                (current_offset * BLOCK_SIZE) / (1024 * 1024),
                None
            )
            
        except Exception as e:
            try:
                temp_img.unlink(missing_ok=True)
            except OSError:
                pass
            return False, 0, 0, str(e)
    
    def convert_all_worker(self):
        """Worker thread for conversion process"""
        if not self.folder_queue:
            self.log_message("No folders in queue to convert")
            return
            
        total_items = len(self.folder_queue)
        self.update_progress(maximum=total_items, value=0)
        
        delete_source = self.delete_source_var.get()
        if delete_source:
            self.log_message(f"Starting conversion of {total_items} folders... (Build for Public Release - will delete source folders)")
        else:
            self.log_message(f"Starting conversion of {total_items} folders...")
        
        success_count = 0
        total_files = 0
        total_size = 0
        folders_to_delete = []  # Track successfully converted folders for deletion
        
        for i, item in enumerate(self.folder_queue):
            self.progress_var.set(f"Converting {i+1}/{total_items}: {item['relative_source']}")
            self.progress_bar.configure(value=i)
            
            self.log_message(f"[{i+1}/{total_items}] Converting: {item['relative_source']}")
            
            # Check if output file exists
            if item['output'].exists():
                self.log_message(f"    Output file exists, overwriting: {item['relative_output']}")
            
            success, file_count, size_mb, _error = self.create_img_from_folder(
                item['folder'],
                item['output']
            )
            
            if success:
                self.log_message(f"    ✓ Success: {file_count} files, {size_mb:.2f} MB")
                success_count += 1
                total_files += file_count
                total_size += size_mb
                
                # Add to deletion list if build for public release is enabled
                if delete_source:
                    folders_to_delete.append(item)
            else:
                self.log_message(f"    ✗ Failed to convert {item['relative_source']}")
        
        # Delete source folders if build for public release is enabled
        if delete_source and folders_to_delete:
            self.log_message("=" * 60)
            self.log_message("Build for Public Release: Deleting source folders...")
            
            deleted_count = 0
            for item in folders_to_delete:
                try:
                    self.log_message(f"Deleting folder: {item['relative_source']}")
                    shutil.rmtree(item['folder'])
                    deleted_count += 1
                    self.log_message(f"    ✓ Deleted: {item['relative_source']}")
                except Exception as e:
                    self.log_message(f"    ✗ Failed to delete {item['relative_source']}: {e}")
            
            self.log_message(f"Deleted {deleted_count}/{len(folders_to_delete)} source folders")
        
        self.progress_bar.configure(value=total_items)
        self.progress_var.set("Conversion completed!")
        
        self.log_message("=" * 60)
        self.log_message(f"Conversion completed!")
        self.log_message(f"Successfully converted: {success_count}/{total_items} archives")
        self.log_message(f"Total files processed: {total_files}")
        self.log_message(f"Total size: {total_size:.2f} MB")
        
        if delete_source and folders_to_delete:
            deleted_count = len([item for item in folders_to_delete if not item['folder'].exists()])
            self.log_message(f"Source folders deleted: {deleted_count}/{len(folders_to_delete)}")
            messagebox.showinfo("Complete", f"Conversion completed!\n{success_count}/{total_items} archives created successfully\n{deleted_count} source folders deleted for public release")
        else:
            messagebox.showinfo("Complete", f"Conversion completed!\n{success_count}/{total_items} archives created successfully")
        
    def convert_all_parallel_worker(self):
        """Build independent archives concurrently across all logical CPUs."""
        queue_snapshot = list(self.folder_queue)
        total_items = len(queue_snapshot)
        if not total_items:
            self.log_message("No folders in queue to convert")
            return

        delete_source = self.delete_source_var.get()
        active_workers = min(self.worker_count, total_items)
        self.update_progress(
            text=f"Starting {total_items} archives with {active_workers} workers...",
            value=0,
            maximum=total_items
        )
        self.log_message(
            f"Starting {total_items} archive builds with "
            f"{active_workers} parallel workers"
        )

        success_count = 0
        total_files = 0
        total_size = 0.0
        folders_to_delete = []

        with ThreadPoolExecutor(
            max_workers=active_workers,
            thread_name_prefix="img-builder"
        ) as executor:
            futures = {
                executor.submit(
                    self.create_img_from_folder,
                    item['folder'],
                    item['output']
                ): item
                for item in queue_snapshot
            }

            for completed, future in enumerate(as_completed(futures), start=1):
                item = futures[future]
                try:
                    success, file_count, size_mb, error = future.result()
                except Exception as exc:
                    success, file_count, size_mb, error = False, 0, 0, str(exc)

                self.update_progress(
                    text=f"Completed {completed}/{total_items}: {item['relative_source']}",
                    value=completed
                )

                if success:
                    success_count += 1
                    total_files += file_count
                    total_size += size_mb
                    if delete_source:
                        folders_to_delete.append(item)
                    self.log_message(
                        f"[{completed}/{total_items}] Success: "
                        f"{item['relative_source']} "
                        f"({file_count} files, {size_mb:.2f} MB)"
                    )
                else:
                    self.log_message(
                        f"[{completed}/{total_items}] Failed: "
                        f"{item['relative_source']} - {error}"
                    )

        deleted_count = 0
        if delete_source:
            self.log_message("Deleting successfully converted source folders...")
            for item in folders_to_delete:
                try:
                    shutil.rmtree(item['folder'])
                    deleted_count += 1
                    self.log_message(f"Deleted: {item['relative_source']}")
                except Exception as exc:
                    self.log_message(
                        f"Failed to delete {item['relative_source']}: {exc}"
                    )

        self.update_progress(text="Conversion completed!", value=total_items)
        self.log_message("=" * 60)
        self.log_message(
            f"Completed: {success_count}/{total_items} archives, "
            f"{total_files} files, {total_size:.2f} MB"
        )
        if delete_source:
            self.log_message(
                f"Source folders deleted: {deleted_count}/{len(folders_to_delete)}"
            )

        summary = (
            f"Conversion completed!\n"
            f"{success_count}/{total_items} archives created successfully"
        )
        if delete_source:
            summary += f"\n{deleted_count} source folders deleted"
        self.root.after(0, messagebox.showinfo, "Complete", summary)

    def start_conversion(self):
        """Start conversion process in separate thread"""
        if not self.game_folder:
            messagebox.showerror("Error", "Please select game folder first")
            return
            
        if not self.folder_queue:
            messagebox.showwarning("Warning", "No folders in queue to convert")
            return
        
        # Show warning if build for public release is enabled
        if self.delete_source_var.get():
            warning_msg = (f"Build for Public Release is ENABLED!\n\n"
                          f"This will PERMANENTLY DELETE {len(self.folder_queue)} source folders after conversion.\n"
                          f"This action cannot be undone!\n\n"
                          f"Are you sure you want to proceed?")
            
            if not messagebox.askyesno("WARNING - Build for Public Release", warning_msg, icon='warning'):
                return
                
        elif messagebox.askyesno("Confirm", f"Convert {len(self.folder_queue)} folders to IMG archives?"):
            pass  # Continue with normal conversion
        else:
            return
            
        # Start conversion in separate thread to prevent GUI freezing
        thread = threading.Thread(
            target=self.convert_all_parallel_worker,
            daemon=True
        )
        thread.start()

    def delete_sources_worker(self):
        """Delete queued source folders without conversion"""
        total_items = len(self.folder_queue)
        self.progress_bar.configure(maximum=total_items, value=0)
        self.log_message(f"Deleting {total_items} source folders without conversion...")
        deleted_count = 0
        failed_count = 0

        # Copy queue to avoid mutation issues during deletion
        queue_snapshot = list(self.folder_queue)

        for i, item in enumerate(queue_snapshot):
            self.progress_var.set(f"Deleting {i+1}/{total_items}: {item['relative_source']}")
            self.progress_bar.configure(value=i+1)

            try:
                shutil.rmtree(item['folder'])
                deleted_count += 1
                self.log_message(f"    ✓ Deleted: {item['relative_source']}")
            except Exception as e:
                failed_count += 1
                self.log_message(f"    ✗ Failed to delete {item['relative_source']}: {e}")

        # Clear queue and tree after deletion attempt
        self.folder_queue.clear()
        for child in self.tree.get_children():
            self.tree.delete(child)

        self.progress_var.set("Deletion completed")
        self.log_message(f"Deletion completed: {deleted_count} deleted, {failed_count} failed")
        messagebox.showinfo("Complete", f"Deletion completed!\nDeleted: {deleted_count}\nFailed: {failed_count}")

    def start_delete_sources_only(self):
        """Ask for confirmation then delete source folders without converting"""
        if not self.game_folder:
            messagebox.showerror("Error", "Please select game folder first")
            return

        if not self.folder_queue:
            messagebox.showwarning("Warning", "No folders in queue to delete")
            return

        warning_msg = (f"This will PERMANENTLY DELETE {len(self.folder_queue)} source folders without creating any IMG files.\n"
                       f"This action cannot be undone. Continue?")

        if not messagebox.askyesno("WARNING - Delete Sources Only", warning_msg, icon='warning'):
            return

        thread = threading.Thread(target=self.delete_sources_worker, daemon=True)
        thread.start()

def main():
    root = tk.Tk()
    app = IMGArchiveCreatorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
