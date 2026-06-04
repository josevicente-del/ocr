Obetivo programar un ocr para a partir de un archivo pdf poder generar uno o varios archivos de salida para poder cargar en un ERP
Los archivos de entrada suelen ser de tipo pdf, que tienen distintas estrucutras, por lo que el ocr debera ser capz de adaptarse a ellas
La estrucutura del pdf es la siguiente:
- Una cabecera con el numero de pedido y la fecha
- Un cuerpo con los productos y sus cantidades, a veces vienen una tabla otras veces viene en formato libre
-Una descrpicion de articulo
-Un tratamiento a realizar  como por ejemplo RAL 7016TXT
ANODIZADO PLATA GRATA
PINO NUDO (BC-1)
ANODIZADADO PLATA GRATA REPULIDA
ANODIZADADO PLATA MATE
LACADO TONO BASE GOLDEN
Hay una relaccion entre el tratamiento del pdf y el que quiero en el archivo de salida
RAL 7016TXT	RAL 7016 TEXTURADO
ANODIZADO PLATA GRATA	GRATADO
PINO NUDO (BC-1)	BASE MADERA TONO 8
ANODIZADADO PLATA GRATA REPULIDA	GRATADO
ANODIZADADO PLATA MATE	PLATA 15 MICRAS
LACADO TONO BASE GOLDEN	ROBLE RUSTICO-S
No todos los tratamientos de los pdf estan definidos para la salida en caso que no se encuentre preguntar
Quiero el programa sea seguro es decir que aunque el pdf no tenga un tratamiento correcto sepa detectarlo y preguntar. Prefiero que tarde mas tiempo pero que sea mas seguro
Debe ser capaz de procesar varias paginas en cada archivo pero debe haber un unico excel de salida
En una misma pagina hay un unico numero de pedido , una una fecha de pedido ,uno o muchos articulos y para cada articulo la cantidad el articulo y el tratamiento
Utiliza metodos de ocr gratuitos pero que sean seguro
Quiero que en la pagina principal aparezcan todos los numeros de pedidos procesados , asi como la cantidad de paginas procesadas y si hubo algun problema 
Tambien queiero el tiempo esperado en terminar el procesamiento
En el archivo de salida quiero que aparezca el numero de pedido, la fecha, el articulo y el tratamiento
En el directorio cosas hay un pdf de ejemplo
Quiero un boton de reset para eliminar los escaneos anteriores y que vuelva a empezar el proceso
Examina el directorio cosas para que lo entiendas todo.
La altura a la que empizan los articulos es fija para todas las paginas.
Debes recuperar tambien el cliente
Debe aparecer la posibilidad de variar el orden en el que apareceran las columas.
El nombre de los articulos tiene un codigo numerico , y despues un texto asociado con elementos que forman parte de un cerramiento de aluminio
Busca las tecnologias que sean mas adecuadas para este proyecto 
