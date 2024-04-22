import tkinter
import customtkinter

DARK_MODE = "dark"
customtkinter.set_appearance_mode(DARK_MODE)
customtkinter.set_default_color_theme("dark-blue")


class App(customtkinter.CTk):

    def __init__(self):
        super().__init__()
        
        self.title("Change Frames")
        # remove title bar , page reducer and closing page !!!most have a quit button with app.destroy!!! (this app have a quit button so don't worry about that)
        self.overrideredirect(True)
        # make the app as big as the screen (no mater wich screen you use) 
        self.geometry("{0}x{1}+0+0".format(self.winfo_screenwidth(), self.winfo_screenheight()))
        

        # root!
        self.main_container = customtkinter.CTkFrame(self, corner_radius=10)
        self.main_container.pack(fill=tkinter.BOTH, expand=True, padx=10, pady=10)

        # left side panel -> for frame selection
        self.left_side_panel = customtkinter.CTkFrame(self.main_container, width=150, corner_radius=10)
        self.left_side_panel.pack(side=tkinter.LEFT, fill=tkinter.Y, expand=False, padx=5, pady=5)
        
        self.left_side_panel.grid_columnconfigure(0, weight=1)
        self.left_side_panel.grid_rowconfigure((0, 1, 2, 3), weight=0)
        self.left_side_panel.grid_rowconfigure((4, 5), weight=1)
        
        
        # self.left_side_panel WIDGET
        self.logo_label = customtkinter.CTkLabel(self.left_side_panel, text="Welcome! \n", font=customtkinter.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        self.scaling_label = customtkinter.CTkLabel(self.left_side_panel, text="UI Scaling:", anchor="w")
        self.scaling_label.grid(row=7, column=0, padx=20, pady=(10, 0))
        
        self.scaling_optionemenu = customtkinter.CTkOptionMenu(self.left_side_panel, values=["80%", "90%", "100%", "110%", "120%"],
                                                            command=self.change_scaling_event)
        self.scaling_optionemenu.grid(row=8, column=0, padx=20, pady=(10, 20), sticky = "s")
        
        self.bt_Quit = customtkinter.CTkButton(self.left_side_panel, text="Quit", fg_color= '#EA0000', hover_color = '#B20000', command= self.close_window)
        self.bt_Quit.grid(row=9, column=0, padx=20, pady=10)
        
        # button to select correct frame IN self.left_side_panel WIDGET
        self.bt_dashboard = customtkinter.CTkButton(self.left_side_panel, text="Dashboard", command=self.dash)
        self.bt_dashboard.grid(row=1, column=0, padx=20, pady=10)

        self.bt_statement = customtkinter.CTkButton(self.left_side_panel, text="Statement", command=self.statement)
        self.bt_statement.grid(row=2, column=0, padx=20, pady=10)
        
        self.bt_categories = customtkinter.CTkButton(self.left_side_panel, text="Manage Categories", command=self.categories)
        self.bt_categories.grid(row=3, column=0, padx=20, pady=10)
        

        # right side panel -> have self.right_dashboard inside it
        self.right_side_panel = customtkinter.CTkFrame(self.main_container, corner_radius=10, fg_color="#000811")
        self.right_side_panel.pack(side=tkinter.LEFT, fill=tkinter.BOTH, expand=True, padx=5, pady=5)
        
        
        self.right_dashboard = customtkinter.CTkFrame(self.main_container, corner_radius=10, fg_color="#000811")
        self.right_dashboard.pack(in_=self.right_side_panel, side=tkinter.TOP, fill=tkinter.BOTH, expand=True, padx=0, pady=0)
        

    #  self.right_dashboard   ----> dashboard widget  
    def dash(self):
        
        self.clear_frame()
        self.bt_from_frame1 = customtkinter.CTkButton(self.right_dashboard, text="dash", command=lambda:print("test dash") )
        self.bt_from_frame1.grid(row=0, column=0, padx=20, pady=(10, 0))
        self.bt_from_frame2 = customtkinter.CTkButton(self.right_dashboard, text="dash 1", command=lambda:print("test dash 1" ) )
        self.bt_from_frame2.grid(row=1, column=0, padx=20, pady=(10, 0))

    #  self.right_dashboard   ----> statement widget
    def statement(self):
        self.clear_frame()
        self.bt_from_frame3 = customtkinter.CTkButton(self.right_dashboard, text="statement", command=lambda:print("test statement") )
        self.bt_from_frame3.grid(row=0, column=0, padx=20, pady=(10, 0))
        
    #  self.right_dashboard   ----> categories widget
    def categories(self):
        self.clear_frame()
        self.bt_from_frame4 = customtkinter.CTkButton(self.right_dashboard, text="categories", command=lambda:print("test cats") )
        self.bt_from_frame4.grid(row=0, column=0, padx=20, pady=(10, 0))


    # Change scaling of all widget 80% to 120%
    def change_scaling_event(self, new_scaling: str):
        new_scaling_float = int(new_scaling.replace("%", "")) / 100
        customtkinter.set_widget_scaling(new_scaling_float)
        
        
    # close the entire window    
    def close_window(self): 
            App.destroy(self)
            
            
    # CLEAR ALL THE WIDGET FROM self.right_dashboard(frame) BEFORE loading the widget of the concerned page       
    def clear_frame(self):
        for widget in self.right_dashboard.winfo_children():
            widget.destroy()


a = App()
a.mainloop()